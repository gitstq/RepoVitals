#!/usr/bin/env python3
"""
RepoHealth - Lightweight Git Repository Health Check Engine.

A zero-dependency Python CLI tool that performs comprehensive health checks
on Git repositories. Supports 10+ check dimensions, colored TUI output,
JSON export, and HTML report generation.

Usage:
    repohealth scan [path]      -- Full scan with TUI table
    repohealth report [path]    -- Generate HTML report
    repohealth json [path]      -- Export JSON report
    repohealth check [path]     -- Quick check (critical items only)
    repohealth history [path]   -- Commit history analysis
    repohealth deps [path]      -- Dependency analysis
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from html import escape as html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# ANSI Color Utilities
# =============================================================================

class Colors:
    """ANSI color code manager. Auto-disables when not running in a TTY."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"

    _enabled: bool = True

    @classmethod
    def enable(cls) -> None:
        """Enable ANSI color output."""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable ANSI color output."""
        cls._enabled = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if color output is currently enabled.

        Returns:
            True if colors are enabled, False otherwise.
        """
        return cls._enabled

    @classmethod
    def auto(cls) -> None:
        """Auto-detect TTY and enable/disable colors accordingly."""
        cls._enabled = sys.stdout.isatty() and sys.stderr.isatty()
        # On Windows, enable ANSI support if available
        if cls._enabled and platform.system() == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                cls._enabled = False

    @classmethod
    def wrap(cls, text: str, color: str) -> str:
        """Wrap text with an ANSI color code.

        Args:
            text: The text to wrap.
            color: The ANSI color code string.

        Returns:
            The color-wrapped text, or plain text if colors are disabled.
        """
        if not cls._enabled:
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def red(cls, text: str) -> str:
        """Return text in red."""
        return cls.wrap(text, cls.RED)

    @classmethod
    def green(cls, text: str) -> str:
        """Return text in green."""
        return cls.wrap(text, cls.GREEN)

    @classmethod
    def yellow(cls, text: str) -> str:
        """Return text in yellow."""
        return cls.wrap(text, cls.YELLOW)

    @classmethod
    def blue(cls, text: str) -> str:
        """Return text in blue."""
        return cls.wrap(text, cls.BLUE)

    @classmethod
    def cyan(cls, text: str) -> str:
        """Return text in cyan."""
        return cls.wrap(text, cls.CYAN)

    @classmethod
    def bold(cls, text: str) -> str:
        """Return text in bold."""
        return cls.wrap(text, cls.BOLD)

    @classmethod
    def dim(cls, text: str) -> str:
        """Return text in dim."""
        return cls.wrap(text, cls.DIM)

    @classmethod
    def score_color(cls, score: float) -> str:
        """Return color based on score value.

        Args:
            score: A score value from 0 to 100.

        Returns:
            ANSI color code string appropriate for the score level.
        """
        if score >= 80:
            return cls.GREEN
        elif score >= 60:
            return cls.YELLOW
        else:
            return cls.RED


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class CheckResult:
    """Result of a single health check dimension.

    Attributes:
        name: Human-readable name of the check dimension.
        score: Score from 0 to 100.
        weight: Weight factor for overall score calculation.
        details: List of detail strings describing findings.
        warnings: List of warning strings for issues found.
        errors: List of error strings for critical issues.
    """

    name: str
    score: float = 0.0
    weight: float = 1.0
    details: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of this check result.
        """
        return asdict(self)


@dataclass
class HealthReport:
    """Complete health report for a repository.

    Attributes:
        repo_path: Absolute path to the repository.
        scan_time: ISO format timestamp of when the scan was performed.
        results: List of individual check results.
        total_score: Weighted overall score from 0 to 100.
    """

    repo_path: str
    scan_time: str
    results: List[CheckResult] = field(default_factory=list)
    total_score: float = 0.0

    def calculate_total(self) -> float:
        """Calculate the weighted total score.

        Returns:
            The weighted average score across all check dimensions.
        """
        if not self.results:
            return 0.0
        total_weight = sum(r.weight for r in self.results)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(r.score * r.weight for r in self.results)
        self.total_score = round(weighted_sum / total_weight, 1)
        return self.total_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of this health report.
        """
        return {
            "repo_path": self.repo_path,
            "scan_time": self.scan_time,
            "total_score": self.total_score,
            "results": [r.to_dict() for r in self.results],
        }


# =============================================================================
# Git Command Helper
# =============================================================================

def run_git(repo_path: str, *args: str, timeout: int = 30) -> Tuple[int, str]:
    """Run a git command in the specified repository.

    Args:
        repo_path: Absolute path to the git repository.
        *args: Git command arguments (e.g., 'log', '--oneline').
        timeout: Maximum execution time in seconds.

    Returns:
        A tuple of (return_code, stdout_output).
    """
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, ""
    except FileNotFoundError:
        return -1, "git not found"
    except OSError as e:
        return -1, str(e)


def is_git_repo(path: str) -> bool:
    """Check if the given path is a valid git repository.

    Args:
        path: Path to check.

    Returns:
        True if the path is a git repository, False otherwise.
    """
    git_dir = os.path.join(path, ".git")
    return os.path.isdir(git_dir) or os.path.isfile(git_dir)


def resolve_repo_path(path: str) -> str:
    """Resolve and validate the repository path.

    Args:
        path: User-provided path (may be relative or '.').

    Returns:
        Absolute path to the repository.

    Raises:
        SystemExit: If the path is not a valid git repository.
    """
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        print(Colors.red(f"Error: Path '{path}' does not exist or is not a directory."))
        sys.exit(1)
    if not is_git_repo(abs_path):
        print(Colors.red(f"Error: '{path}' is not a git repository."))
        sys.exit(1)
    return abs_path


# =============================================================================
# Check: Conventional Commits
# =============================================================================

# Regex pattern for Conventional Commits: type(scope): description
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\(.+\))?"
    r":\s.+",
    re.IGNORECASE,
)


def check_conventional_commits(repo_path: str) -> CheckResult:
    """Check compliance with Conventional Commits specification.

    Analyzes all commit messages in the repository and calculates the
    percentage that follow the Conventional Commits format:
    type(scope): description

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the compliance score and details.
    """
    result = CheckResult(name="Conventional Commits", weight=1.0)
    _, log_output = run_git(repo_path, "log", "--format=%s", "--all")

    if not log_output:
        result.score = 100.0
        result.details.append("No commits found (empty repository)")
        return result

    commits = [line for line in log_output.split("\n") if line.strip()]
    if not commits:
        result.score = 100.0
        result.details.append("No commits found")
        return result

    compliant = 0
    non_compliant_examples: List[str] = []
    type_counter: Counter = Counter()

    for msg in commits:
        if CONVENTIONAL_COMMIT_PATTERN.match(msg.strip()):
            compliant += 1
            commit_type = msg.split("(")[0].split(":")[0].strip().lower()
            type_counter[commit_type] += 1
        else:
            if len(non_compliant_examples) < 5:
                non_compliant_examples.append(msg.strip()[:60])

    total = len(commits)
    ratio = compliant / total if total > 0 else 1.0
    result.score = round(ratio * 100, 1)

    result.details.append(f"Total commits analyzed: {total}")
    result.details.append(f"Conventional commits: {compliant} ({ratio:.1%})")

    if type_counter:
        top_types = type_counter.most_common(5)
        type_str = ", ".join(f"{t}: {c}" for t, c in top_types)
        result.details.append(f"Top types: {type_str}")

    if non_compliant_examples:
        result.warnings.append(f"{total - compliant} non-conventional commits found")
        for ex in non_compliant_examples:
            result.details.append(f"  Non-conventional: \"{ex}\"")

    return result


# =============================================================================
# Check: Branch Health
# =============================================================================

def check_branch_health(repo_path: str) -> CheckResult:
    """Check branch health including stale branches and merge status.

    Evaluates:
    - Number of branches vs. active branches
    - Stale branches (no activity in 90+ days)
    - Unmerged branches

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the branch health score and details.
    """
    result = CheckResult(name="Branch Health", weight=1.0)

    # Get all branches
    rc, branches_output = run_git(repo_path, "branch", "-a", "--format=%(refname:short)|%(committerdate:unix)")
    if rc != 0 or not branches_output:
        result.score = 100.0
        result.details.append("No branches found or unable to read branches")
        return result

    now = datetime.datetime.now().timestamp()
    stale_days_threshold = 90
    stale_threshold_seconds = stale_days_threshold * 86400

    total_branches = 0
    stale_branches: List[str] = []
    branch_names: List[str] = []

    for line in branches_output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 2:
            continue
        branch_name = parts[0].strip()
        branch_names.append(branch_name)
        total_branches += 1

        # Skip remote HEAD references
        if branch_name.endswith("/HEAD"):
            total_branches -= 1
            continue

        try:
            commit_ts = float(parts[1].strip())
            age_seconds = now - commit_ts
            if age_seconds > stale_threshold_seconds:
                stale_branches.append(branch_name)
        except (ValueError, TypeError):
            pass

    # Get default branch
    _, default_output = run_git(repo_path, "symbolic-ref", "--short", "HEAD")
    default_branch = default_output.strip() if default_output else "main/master"

    # Check for unmerged branches
    unmerged_count = 0
    for branch in branch_names:
        if branch.endswith("/HEAD") or branch == default_branch:
            continue
        # Check if branch is merged into default
        rc_merge, _ = run_git(repo_path, "merge-base", "--is-ancestor", branch, default_branch)
        if rc_merge != 0:
            unmerged_count += 1

    # Calculate score
    stale_ratio = len(stale_branches) / total_branches if total_branches > 0 else 0
    unmerged_ratio = unmerged_count / total_branches if total_branches > 0 else 0

    # Deduct points for stale and unmerged branches
    deductions = (stale_ratio * 40) + (unmerged_ratio * 30)
    # Bonus for having a reasonable number of branches
    if total_branches <= 20:
        branch_penalty = 0
    elif total_branches <= 50:
        branch_penalty = 10
    else:
        branch_penalty = 20

    result.score = max(0, round(100 - deductions - branch_penalty, 1))

    result.details.append(f"Total branches: {total_branches}")
    result.details.append(f"Default branch: {default_branch}")
    result.details.append(f"Stale branches (>90 days): {len(stale_branches)}")
    result.details.append(f"Unmerged branches: {unmerged_count}")

    if stale_branches:
        result.warnings.append(f"{len(stale_branches)} stale branch(es) detected")
        for sb in stale_branches[:5]:
            result.details.append(f"  Stale: {sb}")

    if unmerged_count > 10:
        result.warnings.append(f"{unmerged_count} unmerged branches - consider cleanup")

    return result


# =============================================================================
# Check: Repository Size
# =============================================================================

def check_repo_size(repo_path: str) -> CheckResult:
    """Analyze repository size including large files and .gitignore coverage.

    Checks:
    - Total repository size on disk
    - Largest files detected
    - .gitignore presence and coverage
    - Binary file detection

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the repository size analysis score and details.
    """
    result = CheckResult(name="Repository Size", weight=0.8)

    # Calculate total repo size
    total_size = 0
    large_files: List[Tuple[str, int]] = []
    binary_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".wav",
        ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
        ".pyc", ".pyo", ".class", ".o", ".obj",
    }

    tracked_files_count = 0
    binary_count = 0

    # Use git ls-files to get tracked files
    _, ls_output = run_git(repo_path, "ls-files")
    if ls_output:
        for filepath in ls_output.split("\n"):
            if not filepath.strip():
                continue
            tracked_files_count += 1
            full_path = os.path.join(repo_path, filepath)
            try:
                if os.path.isfile(full_path):
                    fsize = os.path.getsize(full_path)
                    total_size += fsize
                    ext = os.path.splitext(filepath)[1].lower()
                    if ext in binary_extensions:
                        binary_count += 1
                    if fsize > 1024 * 1024:  # > 1MB
                        large_files.append((filepath, fsize))
            except OSError:
                pass

    # Sort large files by size
    large_files.sort(key=lambda x: x[1], reverse=True)

    # Check .gitignore
    gitignore_path = os.path.join(repo_path, ".gitignore")
    has_gitignore = os.path.isfile(gitignore_path)
    gitignore_entries = 0
    if has_gitignore:
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            gitignore_entries = sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            )
        except OSError:
            pass

    # Calculate score
    score = 100.0

    # Deduct for large files
    if large_files:
        large_penalty = min(30, len(large_files) * 5)
        score -= large_penalty

    # Deduct for no .gitignore
    if not has_gitignore:
        score -= 20
    elif gitignore_entries < 5:
        score -= 5

    # Deduct for high binary ratio
    if tracked_files_count > 0:
        binary_ratio = binary_count / tracked_files_count
        if binary_ratio > 0.3:
            score -= 15
        elif binary_ratio > 0.15:
            score -= 5

    result.score = max(0, round(score, 1))

    # Format size
    def format_size(size_bytes: int) -> str:
        """Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Human-readable size string.
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    result.details.append(f"Total tracked files: {tracked_files_count}")
    result.details.append(f"Total size: {format_size(total_size)}")
    result.details.append(f"Binary files: {binary_count}")
    result.details.append(f"Large files (>1MB): {len(large_files)}")
    result.details.append(
        f".gitignore: {'present' if has_gitignore else 'MISSING'}"
        + (f" ({gitignore_entries} entries)" if has_gitignore else "")
    )

    if large_files:
        result.warnings.append(f"{len(large_files)} large file(s) detected")
        for fname, fsize in large_files[:5]:
            result.details.append(f"  Large: {fname} ({format_size(fsize)})")

    if not has_gitignore:
        result.errors.append(".gitignore file is missing")

    return result


# =============================================================================
# Check: Dependency Security
# =============================================================================

def check_dependency_security(repo_path: str) -> CheckResult:
    """Check dependency files for version pinning and security concerns.

    Analyzes requirements.txt and package.json for:
    - Presence of dependency files
    - Version pinning (exact versions preferred)
    - Known problematic patterns (latest, *, git+ URLs)

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the dependency security score and details.
    """
    result = CheckResult(name="Dependency Security", weight=1.0)

    has_deps = False
    total_deps = 0
    pinned_deps = 0
    unpinned_deps = 0
    git_deps = 0

    # Check requirements.txt
    req_file = os.path.join(repo_path, "requirements.txt")
    if os.path.isfile(req_file):
        has_deps = True
        try:
            with open(req_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    total_deps += 1
                    # Check for pinned version
                    if re.search(r"==\s*[\d]", line):
                        pinned_deps += 1
                    elif re.search(r">=|<=|!=|~=|<|>", line):
                        pinned_deps += 0.5  # Partial credit for range pins
                    elif re.search(r"git\+", line):
                        git_deps += 1
                    elif "*" in line or "latest" in line.lower():
                        unpinned_deps += 1
                    else:
                        unpinned_deps += 1
        except OSError:
            pass

    # Check for additional requirement files
    for pattern in ["requirements-dev.txt", "requirements/prod.txt", "requirements/base.txt"]:
        extra_req = os.path.join(repo_path, pattern)
        if os.path.isfile(extra_req):
            try:
                with open(extra_req, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("-"):
                            continue
                        total_deps += 1
                        if re.search(r"==\s*[\d]", line):
                            pinned_deps += 1
                        elif re.search(r"git\+", line):
                            git_deps += 1
                        else:
                            unpinned_deps += 1
            except OSError:
                pass

    # Check package.json
    pkg_file = os.path.join(repo_path, "package.json")
    if os.path.isfile(pkg_file):
        has_deps = True
        try:
            with open(pkg_file, "r", encoding="utf-8", errors="replace") as f:
                pkg_content = f.read()
            # Simple JSON parse for dependencies
            try:
                pkg_data = json.loads(pkg_content)
                for dep_section in ["dependencies", "devDependencies"]:
                    deps = pkg_data.get(dep_section, {})
                    for name, version in deps.items():
                        total_deps += 1
                        version_str = str(version)
                        if re.match(r"^\d+\.\d+", version_str):
                            pinned_deps += 1
                        elif version_str.startswith("git+") or version_str.startswith("github:"):
                            git_deps += 1
                        elif version_str in ("*", "latest"):
                            unpinned_deps += 1
                        elif version_str.startswith("^") or version_str.startswith("~"):
                            pinned_deps += 0.5
                        else:
                            unpinned_deps += 1
            except json.JSONDecodeError:
                result.warnings.append("package.json is not valid JSON")
        except OSError:
            pass

    # Check Pipfile
    pipfile = os.path.join(repo_path, "Pipfile")
    if os.path.isfile(pipfile):
        has_deps = True
        result.details.append("Pipfile detected (consider using requirements.txt for pinned deps)")

    # Check pyproject.toml for dependencies
    pyproject_file = os.path.join(repo_path, "pyproject.toml")
    if os.path.isfile(pyproject_file):
        has_deps = True
        try:
            with open(pyproject_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            # Count dependencies in pyproject.toml
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if re.match(r"^dependencies\s*=\s*\[", stripped) or re.match(r'"\[project\.dependencies\]"', stripped):
                    in_deps = True
                elif in_deps and stripped.startswith("]"):
                    in_deps = False
                elif in_deps and stripped and not stripped.startswith("#"):
                    total_deps += 1
                    if re.search(r"==\s*[\d]", stripped):
                        pinned_deps += 1
                    elif re.search(r">=|~=|<|>", stripped):
                        pinned_deps += 0.5
                    else:
                        unpinned_deps += 1
        except OSError:
            pass

    # Calculate score
    if not has_deps:
        result.score = 100.0
        result.details.append("No dependency files found (may not need dependencies)")
        return result

    if total_deps == 0:
        result.score = 100.0
        result.details.append("Dependency files found but empty")
        return result

    pin_ratio = pinned_deps / total_deps
    score = pin_ratio * 80 + 20  # Base 20 for having deps files
    if git_deps > 0:
        score -= min(10, git_deps * 3)
    result.score = max(0, round(score, 1))

    result.details.append(f"Dependency files detected: yes")
    result.details.append(f"Total dependencies: {total_deps}")
    result.details.append(f"Pinned versions: {int(pinned_deps)}")
    result.details.append(f"Unpinned versions: {unpinned_deps}")
    result.details.append(f"Git dependencies: {git_deps}")
    result.details.append(f"Pin rate: {pin_ratio:.1%}")

    if unpinned_deps > 0:
        result.warnings.append(f"{unpinned_deps} unpinned dependenc(ies) detected")

    if git_deps > 0:
        result.warnings.append(f"{git_deps} git-based dependenc(ies) - harder to audit")

    return result


# =============================================================================
# Check: Documentation Completeness
# =============================================================================

def check_documentation(repo_path: str) -> CheckResult:
    """Check documentation completeness for the repository.

    Looks for:
    - README (README.md, README.rst, README.txt, README)
    - LICENSE (LICENSE, LICENSE.md, LICENCE)
    - CONTRIBUTING (CONTRIBUTING.md, CONTRIBUTING.rst)
    - CHANGELOG (CHANGELOG.md, HISTORY.md, CHANGES.md)
    - CODE_OF_CONDUCT
    - docs/ directory
    - API documentation

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the documentation score and details.
    """
    result = CheckResult(name="Documentation", weight=1.0)

    doc_files = {
        "README": ["README.md", "README.rst", "README.txt", "README", "Readme.md"],
        "LICENSE": ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md", "license"],
        "CONTRIBUTING": ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING"],
        "CHANGELOG": ["CHANGELOG.md", "HISTORY.md", "CHANGES.md", "CHANGELOG", "CHANGELOG.rst"],
        "CODE_OF_CONDUCT": ["CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT"],
        "SECURITY": ["SECURITY.md", "SECURITY"],
        "AUTHORS": ["AUTHORS.md", "AUTHORS", "AUTHORS.rst"],
    }

    found_docs: List[str] = []
    missing_docs: List[str] = []
    readme_size = 0

    for doc_type, filenames in doc_files.items():
        found = False
        for filename in filenames:
            filepath = os.path.join(repo_path, filename)
            if os.path.isfile(filepath):
                found = True
                found_docs.append(doc_type)
                if doc_type == "README":
                    try:
                        readme_size = os.path.getsize(filepath)
                    except OSError:
                        pass
                break
        if not found:
            missing_docs.append(doc_type)

    # Check for docs/ directory
    docs_dir = os.path.join(repo_path, "docs")
    has_docs_dir = os.path.isdir(docs_dir)
    if has_docs_dir:
        found_docs.append("docs/ directory")

    # Check for inline docstrings in Python files (sample check)
    python_files_with_docstrings = 0
    python_files_total = 0
    _, ls_output = run_git(repo_path, "ls-files", "*.py")
    if ls_output:
        py_files = [f for f in ls_output.split("\n") if f.endswith(".py")]
        # Sample up to 20 files to avoid slowness
        sample_files = py_files[:20]
        python_files_total = len(py_files)
        for py_file in sample_files:
            full_path = os.path.join(repo_path, py_file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(2048)  # Read first 2KB
                if '"""' in content or "'''" in content:
                    python_files_with_docstrings += 1
            except OSError:
                pass

    # Calculate score
    essential_docs = {"README", "LICENSE"}
    nice_to_have = {"CONTRIBUTING", "CHANGELOG", "CODE_OF_CONDUCT", "SECURITY", "AUTHORS"}

    essential_found = len(found_docs) if found_docs else 0
    essential_count = sum(1 for d in essential_docs if d in found_docs)

    score = 0.0
    # README is critical (30 points)
    if "README" in found_docs:
        score += 25
        if readme_size > 500:  # Non-trivial README
            score += 5
    # LICENSE is critical (20 points)
    if "LICENSE" in found_docs:
        score += 20
    # Each nice-to-have doc is worth 8 points
    for doc in nice_to_have:
        if doc in found_docs:
            score += 8
    # docs/ directory (10 points)
    if has_docs_dir:
        score += 10
    # Docstrings (7 points)
    if python_files_total > 0 and python_files_with_docstrings > 0:
        docstring_ratio = python_files_with_docstrings / min(len(sample_files), python_files_total)
        score += round(docstring_ratio * 7, 1)

    result.score = min(100, round(score, 1))

    result.details.append(f"Found: {', '.join(found_docs) if found_docs else 'none'}")
    if missing_docs:
        result.details.append(f"Missing: {', '.join(missing_docs)}")
    if readme_size > 0:
        result.details.append(f"README size: {readme_size} bytes")
    if python_files_total > 0:
        result.details.append(
            f"Python files with docstrings: {python_files_with_docstrings}/{min(len(sample_files), python_files_total)} (sampled)"
        )

    if "README" not in found_docs:
        result.errors.append("README file is missing")
    if "LICENSE" not in found_docs:
        result.warnings.append("LICENSE file is missing")

    if missing_docs:
        result.warnings.append(f"{len(missing_docs)} documentation file(s) missing")

    return result


# =============================================================================
# Check: Code Complexity
# =============================================================================

def check_code_complexity(repo_path: str) -> CheckResult:
    """Analyze code complexity metrics.

    Checks:
    - Average file length
    - Long files (>500 lines)
    - Long functions (>50 lines)
    - File count by language

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the code complexity score and details.
    """
    result = CheckResult(name="Code Complexity", weight=0.8)

    _, ls_output = run_git(repo_path, "ls-files")
    if not ls_output:
        result.score = 100.0
        result.details.append("No tracked files found")
        return result

    files = [f for f in ls_output.split("\n") if f.strip()]
    if not files:
        result.score = 100.0
        result.details.append("No tracked files found")
        return result

    # Language distribution
    lang_counter: Counter = Counter()
    file_lengths: Dict[str, int] = {}
    total_lines = 0
    long_files: List[Tuple[str, int]] = []
    long_functions_count = 0

    # Extensions to languages mapping
    ext_to_lang = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "JSX", ".tsx": "TSX", ".java": "Java", ".c": "C",
        ".cpp": "C++", ".h": "C/C++ Header", ".hpp": "C++ Header",
        ".cs": "C#", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
        ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin",
        ".scala": "Scala", ".r": "R", ".m": "Objective-C",
        ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
        ".ps1": "PowerShell", ".sql": "SQL", ".html": "HTML",
        ".css": "CSS", ".scss": "SCSS", ".less": "LESS",
        ".vue": "Vue", ".svelte": "Svelte",
    }

    code_extensions = set(ext_to_lang.keys())

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()
        lang = ext_to_lang.get(ext, "Other")
        lang_counter[lang] += 1

        full_path = os.path.join(repo_path, filepath)
        if not os.path.isfile(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            line_count = len(lines)
            file_lengths[filepath] = line_count
            total_lines += line_count

            if ext in code_extensions and line_count > 500:
                long_files.append((filepath, line_count))

            # Detect long functions (simple heuristic: count lines between def/function/func)
            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php"):
                func_start = None
                func_lines = 0
                for line in lines:
                    stripped = line.strip()
                    # Detect function definitions
                    is_func_def = False
                    if ext == ".py" and re.match(r"^(def |async def )", stripped):
                        is_func_def = True
                    elif ext in (".js", ".ts", ".jsx", ".tsx") and re.match(
                        r"^(export\s+)?(async\s+)?function\s", stripped
                    ):
                        is_func_def = True
                    elif ext == ".go" and re.match(r"^func\s", stripped):
                        is_func_def = True
                    elif ext == ".rs" and re.match(r"^(pub\s+)?(async\s+)?fn\s", stripped):
                        is_func_def = True
                    elif ext == ".java" and re.match(r"^(public|private|protected|static|\s)*\s*\w+\s+\w+\s*\(", stripped):
                        is_func_def = True

                    if is_func_def:
                        if func_start is not None and func_lines > 50:
                            long_functions_count += 1
                        func_start = True
                        func_lines = 0
                    elif func_start is not None:
                        if stripped == "" and func_lines == 0:
                            continue
                        func_lines += 1

                # Check last function
                if func_start is not None and func_lines > 50:
                    long_functions_count += 1

        except OSError:
            pass

    # Calculate score
    score = 100.0
    avg_lines = total_lines / len(files) if files else 0

    # Penalize long files
    if long_files:
        score -= min(25, len(long_files) * 5)

    # Penalize long functions
    if long_functions_count > 0:
        score -= min(20, long_functions_count * 4)

    # Penalize very high average
    if avg_lines > 300:
        score -= 10
    elif avg_lines > 200:
        score -= 5

    result.score = max(0, round(score, 1))

    # Top languages
    top_langs = lang_counter.most_common(5)
    lang_str = ", ".join(f"{lang}: {count}" for lang, count in top_langs)
    result.details.append(f"Total files: {len(files)}")
    result.details.append(f"Total lines: {total_lines:,}")
    result.details.append(f"Average lines/file: {avg_lines:.0f}")
    result.details.append(f"Languages: {lang_str}")
    result.details.append(f"Long files (>500 lines): {len(long_files)}")
    result.details.append(f"Long functions (>50 lines): {long_functions_count}")

    if long_files:
        result.warnings.append(f"{len(long_files)} long file(s) detected")
        for fname, flen in long_files[:5]:
            result.details.append(f"  Long: {fname} ({flen} lines)")

    if long_functions_count > 0:
        result.warnings.append(f"{long_functions_count} long function(s) detected")

    return result


# =============================================================================
# Check: Git History Analysis
# =============================================================================

def check_git_history(repo_path: str) -> CheckResult:
    """Analyze git commit history for activity patterns.

    Analyzes:
    - Commit frequency (commits per week/month)
    - Contributor distribution
    - Activity trends (recent vs. historical)
    - Commit message quality

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the git history analysis score and details.
    """
    result = CheckResult(name="Git History", weight=1.0)

    # Get commit log with dates and authors
    _, log_output = run_git(
        repo_path, "log", "--all", "--format=%ai|%an|%s", "--date=iso"
    )
    if not log_output:
        result.score = 50.0
        result.details.append("No commits found")
        return result

    commits = []
    for line in log_output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) >= 2:
            commits.append({
                "date": parts[0].strip(),
                "author": parts[1].strip(),
                "message": parts[2].strip() if len(parts) > 2 else "",
            })

    if not commits:
        result.score = 50.0
        result.details.append("No parseable commits found")
        return result

    total_commits = len(commits)

    # Parse dates and calculate activity
    now = datetime.datetime.now()
    commits_by_week: Counter = Counter()
    commits_by_month: Counter = Counter()
    commits_by_author: Counter = Counter()
    recent_commits = 0  # Last 30 days
    very_recent_commits = 0  # Last 7 days

    thirty_days_ago = now - datetime.timedelta(days=30)
    seven_days_ago = now - datetime.timedelta(days=7)

    for commit in commits:
        author = commit["author"]
        commits_by_author[author] += 1

        try:
            commit_date = datetime.datetime.fromisoformat(commit["date"].split("+")[0].split(" ")[0])
            week_key = commit_date.strftime("%Y-W%W")
            month_key = commit_date.strftime("%Y-%m")
            commits_by_week[week_key] += 1
            commits_by_month[month_key] += 1

            if commit_date >= thirty_days_ago:
                recent_commits += 1
            if commit_date >= seven_days_ago:
                very_recent_commits += 1
        except (ValueError, IndexError):
            pass

    # Calculate metrics
    num_weeks = len(commits_by_week)
    num_months = len(commits_by_month)
    avg_commits_per_week = total_commits / num_weeks if num_weeks > 0 else 0
    avg_commits_per_month = total_commits / num_months if num_months > 0 else 0

    num_contributors = len(commits_by_author)
    top_contributor = commits_by_author.most_common(1)[0] if commits_by_author else ("Unknown", 0)
    top_contributor_ratio = top_contributor[1] / total_commits if total_commits > 0 else 0

    # Bus factor (how many people do 50% of commits)
    sorted_contribs = sorted(commits_by_author.values(), reverse=True)
    cumulative = 0
    bus_factor = 0
    for count in sorted_contribs:
        cumulative += count
        bus_factor += 1
        if cumulative >= total_commits * 0.5:
            break

    # Calculate score
    score = 50.0  # Base score

    # Activity recency bonus (up to 20 points)
    if very_recent_commits > 0:
        score += 15
    elif recent_commits > 0:
        score += 10
    elif recent_commits == 0 and total_commits > 0:
        score -= 10  # Inactive repo penalty

    # Commit frequency bonus (up to 15 points)
    if avg_commits_per_week >= 5:
        score += 15
    elif avg_commits_per_week >= 2:
        score += 10
    elif avg_commits_per_week >= 1:
        score += 5

    # Contributor diversity bonus (up to 15 points)
    if num_contributors >= 5:
        score += 15
    elif num_contributors >= 3:
        score += 10
    elif num_contributors >= 2:
        score += 5

    # Bus factor bonus (up to 10 points)
    if bus_factor >= 4:
        score += 10
    elif bus_factor >= 3:
        score += 7
    elif bus_factor >= 2:
        score += 3

    # Penalize single-contributor dominance
    if top_contributor_ratio > 0.9 and num_contributors > 1:
        score -= 5

    result.score = max(0, min(100, round(score, 1)))

    result.details.append(f"Total commits: {total_commits}")
    result.details.append(f"Contributors: {num_contributors}")
    result.details.append(f"Active weeks: {num_weeks}")
    result.details.append(f"Avg commits/week: {avg_commits_per_week:.1f}")
    result.details.append(f"Avg commits/month: {avg_commits_per_month:.1f}")
    result.details.append(f"Bus factor: {bus_factor}")
    result.details.append(f"Commits (last 7 days): {very_recent_commits}")
    result.details.append(f"Commits (last 30 days): {recent_commits}")
    result.details.append(f"Top contributor: {top_contributor[0]} ({top_contributor[1]} commits, {top_contributor_ratio:.1%})")

    if recent_commits == 0 and total_commits > 0:
        result.warnings.append("No commits in the last 30 days - repository may be inactive")

    if bus_factor == 1:
        result.warnings.append("Bus factor is 1 - single person dependency risk")

    if top_contributor_ratio > 0.9 and num_contributors > 1:
        result.warnings.append(f"Top contributor has {top_contributor_ratio:.1%} of all commits")

    return result


# =============================================================================
# Check: Security Baseline
# =============================================================================

# Patterns for sensitive files that should not be in the repository
SENSITIVE_FILE_PATTERNS = [
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging",
    ".env.test", ".env.backup",
    "credentials.json", "credentials.xml", "credentials.yml", "credentials.yaml",
    "secret_key", "secret_key.txt", "secret_key.py",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    ".pem", ".key", ".p12", ".pfx", ".jks",
    "application.properties", "application.yml", "application-local.yml",
    "webpack.config.js",  # Often contains API keys in tutorials
]

SENSITIVE_CONTENT_PATTERNS = [
    (r"(?i)password\s*=\s*\S+", "Hardcoded password detected"),
    (r"(?i)api[_-]?key\s*=\s*\S+", "Hardcoded API key detected"),
    (r"(?i)secret[_-]?key\s*=\s*\S+", "Hardcoded secret key detected"),
    (r"(?i)token\s*=\s*\S+", "Hardcoded token detected"),
    (r"(?i)aws[_-]?access[_-]?key\s*=\s*\S+", "AWS access key detected"),
    (r"(?i)aws[_-]?secret\s*=\s*\S+", "AWS secret detected"),
    (r"-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----", "Private key detected"),
    (r"(?i)github[_-]?token\s*=\s*\S+", "GitHub token detected"),
    (r"(?i)slack[_-]?token\s*=\s*\S+", "Slack token detected"),
    (r"(?i)database[_-]?url\s*=\s*\S+", "Database URL detected"),
]


def check_security_baseline(repo_path: str) -> CheckResult:
    """Check for security baseline issues.

    Detects:
    - Sensitive files (.env, credentials, keys)
    - Hardcoded secrets in source code
    - Private keys
    - Configuration files with secrets

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the security baseline score and details.
    """
    result = CheckResult(name="Security Baseline", weight=1.2)

    _, ls_output = run_git(repo_path, "ls-files")
    if not ls_output:
        result.score = 100.0
        result.details.append("No tracked files found")
        return result

    files = [f for f in ls_output.split("\n") if f.strip()]

    # Check for sensitive files
    sensitive_files_found: List[str] = []
    for filepath in files:
        filename = os.path.basename(filepath)
        for pattern in SENSITIVE_FILE_PATTERNS:
            if filename == pattern or filename.endswith(pattern):
                sensitive_files_found.append(filepath)
                break

    # Check for sensitive content in tracked files (sample)
    sensitive_content_found: List[Tuple[str, str]] = []
    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
                       ".rb", ".php", ".yml", ".yaml", ".json", ".xml", ".properties",
                       ".cfg", ".ini", ".conf", ".sh", ".bash", ".env", ".toml"}
    # Only scan a sample of files to avoid slowness
    sample_files = [f for f in files if os.path.splitext(f)[1].lower() in code_extensions][:50]

    for filepath in sample_files:
        full_path = os.path.join(repo_path, filepath)
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for pattern, description in SENSITIVE_CONTENT_PATTERNS:
                if re.search(pattern, content):
                    sensitive_content_found.append((filepath, description))
                    break  # One match per file is enough
        except OSError:
            pass

    # Check .gitignore for sensitive patterns
    gitignore_path = os.path.join(repo_path, ".gitignore")
    gitignore_has_env = False
    gitignore_has_keys = False
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                gitignore_content = f.read().lower()
            gitignore_has_env = ".env" in gitignore_content
            gitignore_has_keys = any(
                pattern in gitignore_content
                for pattern in [".pem", ".key", "credentials", "secret"]
            )
        except OSError:
            pass

    # Calculate score
    score = 100.0
    score -= len(sensitive_files_found) * 15
    score -= len(sensitive_content_found) * 10
    if not gitignore_has_env and sensitive_files_found:
        score -= 5
    if not gitignore_has_keys:
        score -= 3

    result.score = max(0, round(score, 1))

    result.details.append(f"Sensitive files found: {len(sensitive_files_found)}")
    result.details.append(f"Sensitive content found: {len(sensitive_content_found)}")
    result.details.append(f".gitignore covers .env: {'yes' if gitignore_has_env else 'no'}")
    result.details.append(f".gitignore covers keys: {'yes' if gitignore_has_keys else 'no'}")

    for sf in sensitive_files_found[:5]:
        result.errors.append(f"Sensitive file tracked: {sf}")

    for filepath, description in sensitive_content_found[:5]:
        result.errors.append(f"{description} in {filepath}")

    if sensitive_files_found:
        result.warnings.append(
            f"{len(sensitive_files_found)} sensitive file(s) should not be tracked"
        )

    if sensitive_content_found:
        result.warnings.append(
            f"{len(sensitive_content_found)} file(s) may contain hardcoded secrets"
        )

    return result


# =============================================================================
# Check: CI/CD Configuration
# =============================================================================

CI_CONFIG_FILES = {
    "GitHub Actions": [".github/workflows/", ".github/workflows/*.yml", ".github/workflows/*.yaml"],
    "GitLab CI": [".gitlab-ci.yml", ".gitlab-ci.yaml"],
    "Travis CI": [".travis.yml", ".travis.yaml"],
    "CircleCI": [".circleci/config.yml"],
    "Jenkins": ["Jenkinsfile", "jenkinsfile"],
    "Azure Pipelines": ["azure-pipelines.yml", "azure-pipelines.yaml"],
    "Bitbucket Pipelines": ["bitbucket-pipelines.yml"],
    "Drone CI": [".drone.yml"],
    "GitHub Actions (legacy)": [".github/workflows/*.yml"],
}


def check_cicd_config(repo_path: str) -> CheckResult:
    """Detect CI/CD configuration and assess pipeline coverage.

    Checks for:
    - Presence of CI/CD configuration files
    - Build/test/deploy stages
    - Multiple environment support

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the CI/CD configuration score and details.
    """
    result = CheckResult(name="CI/CD Configuration", weight=0.8)

    found_configs: List[str] = []
    has_test_job = False
    has_build_job = False
    has_deploy_job = False

    # Check for CI config files
    # GitHub Actions
    github_workflows_dir = os.path.join(repo_path, ".github", "workflows")
    if os.path.isdir(github_workflows_dir):
        found_configs.append("GitHub Actions")
        for wf_file in os.listdir(github_workflows_dir):
            if wf_file.endswith((".yml", ".yaml")):
                wf_path = os.path.join(github_workflows_dir, wf_file)
                try:
                    with open(wf_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read().lower()
                    if "test" in content:
                        has_test_job = True
                    if "build" in content:
                        has_build_job = True
                    if "deploy" in content:
                        has_deploy_job = True
                except OSError:
                    pass

    # GitLab CI
    for gl_file in [".gitlab-ci.yml", ".gitlab-ci.yaml"]:
        gl_path = os.path.join(repo_path, gl_file)
        if os.path.isfile(gl_path):
            found_configs.append("GitLab CI")
            try:
                with open(gl_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                if "test" in content:
                    has_test_job = True
                if "build" in content or "compile" in content:
                    has_build_job = True
                if "deploy" in content or "production" in content:
                    has_deploy_job = True
            except OSError:
                pass
            break

    # Travis CI
    travis_path = os.path.join(repo_path, ".travis.yml")
    if os.path.isfile(travis_path):
        found_configs.append("Travis CI")
        try:
            with open(travis_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().lower()
            if "script" in content or "test" in content:
                has_test_job = True
            if "deploy" in content:
                has_deploy_job = True
        except OSError:
            pass

    # CircleCI
    circle_path = os.path.join(repo_path, ".circleci", "config.yml")
    if os.path.isfile(circle_path):
        found_configs.append("CircleCI")
        try:
            with open(circle_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().lower()
            if "test" in content:
                has_test_job = True
            if "deploy" in content:
                has_deploy_job = True
        except OSError:
            pass

    # Jenkins
    for jfile in ["Jenkinsfile", "jenkinsfile"]:
        jpath = os.path.join(repo_path, jfile)
        if os.path.isfile(jpath):
            found_configs.append("Jenkins")
            try:
                with open(jpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                if "test" in content:
                    has_test_job = True
                if "build" in content:
                    has_build_job = True
                if "deploy" in content:
                    has_deploy_job = True
            except OSError:
                pass
            break

    # Azure Pipelines
    for az_file in ["azure-pipelines.yml", "azure-pipelines.yaml"]:
        az_path = os.path.join(repo_path, az_file)
        if os.path.isfile(az_path):
            found_configs.append("Azure Pipelines")
            try:
                with open(az_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                if "test" in content:
                    has_test_job = True
                if "build" in content:
                    has_build_job = True
                if "deploy" in content:
                    has_deploy_job = True
            except OSError:
                pass
            break

    # Bitbucket Pipelines
    bb_path = os.path.join(repo_path, "bitbucket-pipelines.yml")
    if os.path.isfile(bb_path):
        found_configs.append("Bitbucket Pipelines")

    # Calculate score
    score = 0.0
    if found_configs:
        score += 40  # Has CI/CD
        if has_test_job:
            score += 25
        if has_build_job:
            score += 15
        if has_deploy_job:
            score += 20
    else:
        score = 20.0  # No CI/CD at all - minimal score

    result.score = min(100, round(score, 1))

    result.details.append(f"CI/CD detected: {', '.join(found_configs) if found_configs else 'none'}")
    result.details.append(f"Has test job: {'yes' if has_test_job else 'no'}")
    result.details.append(f"Has build job: {'yes' if has_build_job else 'no'}")
    result.details.append(f"Has deploy job: {'yes' if has_deploy_job else 'no'}")

    if not found_configs:
        result.warnings.append("No CI/CD configuration detected")
    elif not has_test_job:
        result.warnings.append("CI/CD config found but no test job detected")

    return result


# =============================================================================
# Check: Repository Metadata
# =============================================================================

def check_repo_metadata(repo_path: str) -> CheckResult:
    """Check repository metadata completeness.

    Examines:
    - Repository description (from git config or README)
    - Topics/keywords
    - Homepage URL
    - Repository name conventions
    - .editorconfig presence
    - .gitattributes presence

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A CheckResult with the metadata score and details.
    """
    result = CheckResult(name="Repository Metadata", weight=0.6)

    score = 0.0
    details: List[str] = []

    # Check git config for description
    _, description = run_git(repo_path, "config", "--get", "remote.origin.url")
    has_remote = bool(description and description != "git not found")

    # Check for description in git
    _, git_desc = run_git(repo_path, "config", "--get", "repo.description")
    has_description = bool(git_desc and git_desc != "")

    # Check README for project description (first line)
    readme_path = None
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        if os.path.isfile(os.path.join(repo_path, name)):
            readme_path = os.path.join(repo_path, name)
            break

    has_readme = readme_path is not None
    readme_has_badge = False
    readme_has_badges = False
    readme_has_install = False
    readme_has_usage = False
    readme_has_license_section = False

    if readme_path:
        try:
            with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                readme_content = f.read()
            readme_lower = readme_content.lower()

            # Check for badges
            badge_count = readme_lower.count("badge") + readme_lower.count("shields.io")
            if badge_count >= 2:
                readme_has_badges = True
                score += 5
            elif badge_count >= 1:
                readme_has_badge = True
                score += 2

            # Check for installation section
            if any(kw in readme_lower for kw in ["installation", "install", "getting started", "quick start"]):
                readme_has_install = True
                score += 10

            # Check for usage section
            if any(kw in readme_lower for kw in ["usage", "example", "how to use", "tutorial"]):
                readme_has_usage = True
                score += 10

            # Check for license section
            if "license" in readme_lower or "licence" in readme_lower:
                readme_has_license_section = True
                score += 5

        except OSError:
            pass

    # Check for .editorconfig
    has_editorconfig = os.path.isfile(os.path.join(repo_path, ".editorconfig"))
    if has_editorconfig:
        score += 5

    # Check for .gitattributes
    has_gitattributes = os.path.isfile(os.path.join(repo_path, ".gitattributes"))
    if has_gitattributes:
        score += 5

    # Check for .gitmodules (monorepo indicator)
    has_submodules = os.path.isfile(os.path.join(repo_path, ".gitmodules"))

    # Check for homepage in package.json or setup.py
    has_homepage = False
    pkg_file = os.path.join(repo_path, "package.json")
    if os.path.isfile(pkg_file):
        try:
            with open(pkg_file, "r", encoding="utf-8", errors="replace") as f:
                pkg_data = json.loads(f.read())
            if pkg_data.get("homepage") or pkg_data.get("url"):
                has_homepage = True
                score += 5
        except (OSError, json.JSONDecodeError):
            pass

    setup_file = os.path.join(repo_path, "setup.py")
    if os.path.isfile(setup_file) and not has_homepage:
        try:
            with open(setup_file, "r", encoding="utf-8", errors="replace") as f:
                setup_content = f.read().lower()
            if "url" in setup_content or "homepage" in setup_content:
                has_homepage = True
                score += 5
        except OSError:
            pass

    # Base score for having remote
    if has_remote:
        score += 10
    if has_description:
        score += 10
    if has_readme:
        score += 15

    result.score = min(100, round(score, 1))

    details.append(f"Has remote: {'yes' if has_remote else 'no'}")
    details.append(f"Has description: {'yes' if has_description else 'no'}")
    details.append(f"Has README: {'yes' if has_readme else 'no'}")
    details.append(f"Has homepage: {'yes' if has_homepage else 'no'}")
    details.append(f"Has .editorconfig: {'yes' if has_editorconfig else 'no'}")
    details.append(f"Has .gitattributes: {'yes' if has_gitattributes else 'no'}")
    details.append(f"README has badges: {'yes' if readme_has_badges else 'no'}")
    details.append(f"README has install section: {'yes' if readme_has_install else 'no'}")
    details.append(f"README has usage section: {'yes' if readme_has_usage else 'no'}")
    details.append(f"README has license section: {'yes' if readme_has_license_section else 'no'}")

    if has_submodules:
        details.append("Git submodules detected")

    result.details.extend(details)

    if not has_readme:
        result.errors.append("README file is missing")
    if not has_remote:
        result.warnings.append("No remote origin configured")
    if not has_description:
        result.warnings.append("No repository description set")

    return result


# =============================================================================
# Report Formatters
# =============================================================================

def format_tui_report(report: HealthReport) -> str:
    """Format the health report as a colored TUI table.

    Args:
        report: The complete health report.

    Returns:
        A formatted string with ANSI color codes for terminal display.
    """
    lines: List[str] = []

    # Header
    lines.append("")
    lines.append(Colors.bold("=" * 72))
    lines.append(Colors.bold(Colors.cyan("  RepoHealth - Git Repository Health Check")))
    lines.append(Colors.bold("=" * 72))
    lines.append("")
    lines.append(f"  Repository: {Colors.bold(report.repo_path)}")
    lines.append(f"  Scan Time:  {report.scan_time}")
    lines.append("")

    # Score bar
    score = report.total_score
    score_clr = Colors.score_color(score)
    bar_width = 40
    filled = int(bar_width * score / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    lines.append(f"  Overall Score: {Colors.bold(Colors.wrap(f'{score}/100', score_clr))}")
    lines.append(f"  [{Colors.wrap(bar, score_clr)}]")
    lines.append("")

    # Rating
    if score >= 90:
        rating = Colors.green("EXCELLENT")
    elif score >= 80:
        rating = Colors.green("GOOD")
    elif score >= 70:
        rating = Colors.yellow("FAIR")
    elif score >= 60:
        rating = Colors.yellow("NEEDS IMPROVEMENT")
    elif score >= 40:
        rating = Colors.red("POOR")
    else:
        rating = Colors.red("CRITICAL")
    lines.append(f"  Rating: {Colors.bold(rating)}")
    lines.append("")

    # Results table
    lines.append(Colors.bold("-" * 72))
    lines.append(Colors.bold(f"  {'Check Dimension':<30} {'Score':>8} {'Weight':>8} {'Status':>12}"))
    lines.append(Colors.bold("-" * 72))

    for r in report.results:
        score_color = Colors.score_color(r.score)
        if r.score >= 80:
            status = Colors.green("PASS")
        elif r.score >= 60:
            status = Colors.yellow("WARN")
        else:
            status = Colors.red("FAIL")

        name_display = r.name[:28] + ".." if len(r.name) > 30 else r.name
        row_clr = Colors.score_color(r.score)
        lines.append(
            f"  {name_display:<30} "
            f"{Colors.wrap(f'{r.score:>7.1f}', row_clr)} "
            f"{r.weight:>8.1f} "
            f"{status:>12}"
        )

    lines.append(Colors.bold("-" * 72))
    lines.append("")

    # Details for each check
    for r in report.results:
        lines.append(Colors.bold(f"  [{r.name}]"))
        for detail in r.details:
            lines.append(f"    {Colors.dim(detail)}")
        for warning in r.warnings:
            lines.append(f"    {Colors.yellow('!')} {warning}")
        for error in r.errors:
            lines.append(f"    {Colors.red('x')} {error}")
        lines.append("")

    lines.append(Colors.bold("=" * 72))
    lines.append("")

    return "\n".join(lines)


def format_json_report(report: HealthReport) -> str:
    """Format the health report as JSON.

    Args:
        report: The complete health report.

    Returns:
        A JSON string representation of the report.
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def format_html_report(report: HealthReport) -> str:
    """Format the health report as a self-contained HTML document.

    Generates a single HTML file with embedded CSS styling,
    including score visualization, detailed tables, and
    dimension-specific breakdowns.

    Args:
        report: The complete health report.

    Returns:
        A complete HTML document string.
    """
    score = report.total_score

    # Determine rating
    if score >= 90:
        rating = "Excellent"
        rating_class = "excellent"
    elif score >= 80:
        rating = "Good"
        rating_class = "good"
    elif score >= 70:
        rating = "Fair"
        rating_class = "fair"
    elif score >= 60:
        rating = "Needs Improvement"
        rating_class = "needs-improvement"
    elif score >= 40:
        rating = "Poor"
        rating_class = "poor"
    else:
        rating = "Critical"
        rating_class = "critical"

    # Build results rows
    results_rows = ""
    for r in report.results:
        if r.score >= 80:
            status = '<span class="badge badge-pass">PASS</span>'
        elif r.score >= 60:
            status = '<span class="badge badge-warn">WARN</span>'
        else:
            status = '<span class="badge badge-fail">FAIL</span>'

        details_html = ""
        for d in r.details:
            details_html += f'<div class="detail-item">{html_escape(d)}</div>'
        for w in r.warnings:
            details_html += f'<div class="detail-item warning">{html_escape(w)}</div>'
        for e in r.errors:
            details_html += f'<div class="detail-item error">{html_escape(e)}</div>'

        results_rows += f"""
        <tr class="result-row">
            <td class="result-name">{html_escape(r.name)}</td>
            <td class="result-score">
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {r.score}%; background: {get_score_color(r.score)};"></div>
                </div>
                <span class="score-value">{r.score:.1f}</span>
            </td>
            <td class="result-weight">{r.weight:.1f}</td>
            <td class="result-status">{status}</td>
        </tr>
        <tr class="detail-row">
            <td colspan="4">
                <div class="details-panel">{details_html}</div>
            </td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RepoHealth Report - {html_escape(os.path.basename(report.repo_path))}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
        }}
        .header h1 {{
            font-size: 2rem;
            color: #58a6ff;
            margin-bottom: 0.5rem;
        }}
        .header .subtitle {{ color: #8b949e; font-size: 0.9rem; }}
        .meta {{ color: #8b949e; margin-top: 1rem; font-size: 0.85rem; }}
        .score-section {{
            text-align: center;
            padding: 2rem;
            background: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
            margin-bottom: 2rem;
        }}
        .score-circle {{
            width: 160px;
            height: 160px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            font-weight: bold;
            color: white;
            margin-bottom: 1rem;
        }}
        .score-circle.excellent {{ background: linear-gradient(135deg, #238636, #2ea043); }}
        .score-circle.good {{ background: linear-gradient(135deg, #1a7f37, #238636); }}
        .score-circle.fair {{ background: linear-gradient(135deg, #9e6a03, #bb8009); }}
        .score-circle.needs-improvement {{ background: linear-gradient(135deg, #9e6a03, #d29922); }}
        .score-circle.poor {{ background: linear-gradient(135deg, #da3633, #f85149); }}
        .score-circle.critical {{ background: linear-gradient(135deg, #b62324, #da3633); }}
        .rating {{ font-size: 1.2rem; color: #8b949e; }}
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #30363d;
            margin-bottom: 2rem;
        }}
        .results-table th {{
            background: #21262d;
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.85rem;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .result-row td {{ padding: 0.75rem 1rem; border-top: 1px solid #30363d; }}
        .result-row:hover {{ background: #1c2128; }}
        .result-name {{ font-weight: 500; color: #c9d1d9; }}
        .result-score {{ width: 200px; }}
        .score-bar-container {{
            display: inline-block;
            width: 100px;
            height: 8px;
            background: #30363d;
            border-radius: 4px;
            overflow: hidden;
            vertical-align: middle;
            margin-right: 0.5rem;
        }}
        .score-bar {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}
        .score-value {{ font-size: 0.9rem; font-weight: 600; }}
        .result-weight {{ color: #8b949e; text-align: center; }}
        .result-status {{ text-align: center; }}
        .badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-pass {{ background: #12261e; color: #3fb950; }}
        .badge-warn {{ background: #2a1f00; color: #d29922; }}
        .badge-fail {{ background: #2a0e0e; color: #f85149; }}
        .detail-row td {{ padding: 0; border-top: 1px solid #30363d; }}
        .details-panel {{
            padding: 0.75rem 1rem 0.75rem 2rem;
            background: #0d1117;
            display: none;
        }}
        .detail-row:hover .details-panel {{ display: block; }}
        .detail-item {{
            font-size: 0.8rem;
            color: #8b949e;
            padding: 0.15rem 0;
        }}
        .detail-item.warning {{ color: #d29922; }}
        .detail-item.error {{ color: #f85149; }}
        .footer {{
            text-align: center;
            padding: 1rem;
            color: #484f58;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RepoHealth Report</h1>
            <div class="subtitle">Git Repository Health Check</div>
            <div class="meta">
                Repository: {html_escape(report.repo_path)}<br>
                Scan Time: {html_escape(report.scan_time)}
            </div>
        </div>

        <div class="score-section">
            <div class="score-circle {rating_class}">{score:.0f}</div>
            <div class="rating">Rating: {rating}</div>
        </div>

        <table class="results-table">
            <thead>
                <tr>
                    <th>Check Dimension</th>
                    <th>Score</th>
                    <th>Weight</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {results_rows}
            </tbody>
        </table>

        <div class="footer">
            Generated by RepoHealth v1.0.0
        </div>
    </div>
</body>
</html>"""

    return html


def get_score_color(score: float) -> str:
    """Get a hex color code based on score value.

    Args:
        score: A score from 0 to 100.

    Returns:
        A hex color string.
    """
    if score >= 80:
        return "#3fb950"
    elif score >= 60:
        return "#d29922"
    else:
        return "#f85149"


# =============================================================================
# Scan Engine
# =============================================================================

def run_full_scan(repo_path: str) -> HealthReport:
    """Run all health check dimensions on the repository.

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A complete HealthReport with all check results.
    """
    report = HealthReport(
        repo_path=repo_path,
        scan_time=datetime.datetime.now().isoformat(),
    )

    # Run all checks
    report.results.append(check_conventional_commits(repo_path))
    report.results.append(check_branch_health(repo_path))
    report.results.append(check_repo_size(repo_path))
    report.results.append(check_dependency_security(repo_path))
    report.results.append(check_documentation(repo_path))
    report.results.append(check_code_complexity(repo_path))
    report.results.append(check_git_history(repo_path))
    report.results.append(check_security_baseline(repo_path))
    report.results.append(check_cicd_config(repo_path))
    report.results.append(check_repo_metadata(repo_path))

    report.calculate_total()
    return report


def run_quick_check(repo_path: str) -> HealthReport:
    """Run only critical health checks.

    Performs a subset of checks focused on security and essential items:
    - Security Baseline
    - Documentation (README + LICENSE)
    - CI/CD Configuration

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A HealthReport with only critical check results.
    """
    report = HealthReport(
        repo_path=repo_path,
        scan_time=datetime.datetime.now().isoformat(),
    )

    report.results.append(check_security_baseline(repo_path))
    report.results.append(check_documentation(repo_path))
    report.results.append(check_cicd_config(repo_path))

    report.calculate_total()
    return report


def run_history_analysis(repo_path: str) -> HealthReport:
    """Run detailed commit history analysis.

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A HealthReport focused on git history analysis.
    """
    report = HealthReport(
        repo_path=repo_path,
        scan_time=datetime.datetime.now().isoformat(),
    )

    report.results.append(check_git_history(repo_path))
    report.results.append(check_conventional_commits(repo_path))

    report.calculate_total()
    return report


def run_deps_analysis(repo_path: str) -> HealthReport:
    """Run dependency-focused analysis.

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        A HealthReport focused on dependency analysis.
    """
    report = HealthReport(
        repo_path=repo_path,
        scan_time=datetime.datetime.now().isoformat(),
    )

    report.results.append(check_dependency_security(repo_path))

    report.calculate_total()
    return report


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_scan(args: argparse.Namespace) -> None:
    """Handle the 'scan' CLI command.

    Performs a full health scan and displays results in the terminal.

    Args:
        args: Parsed command-line arguments with 'path' attribute.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_full_scan(repo_path)
    print(format_tui_report(report))


def cmd_report(args: argparse.Namespace) -> None:
    """Handle the 'report' CLI command.

    Generates an HTML report file.

    Args:
        args: Parsed command-line arguments with 'path' and 'output' attributes.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_full_scan(repo_path)

    output_path = args.output
    if not output_path:
        repo_name = os.path.basename(repo_path)
        output_path = os.path.join(os.getcwd(), f"{repo_name}_health_report.html")

    html_content = format_html_report(report)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(Colors.green(f"HTML report saved to: {output_path}"))
    except OSError as e:
        print(Colors.red(f"Error writing report: {e}"))
        sys.exit(1)


def cmd_json(args: argparse.Namespace) -> None:
    """Handle the 'json' CLI command.

    Exports the health report as JSON.

    Args:
        args: Parsed command-line arguments with 'path' and 'output' attributes.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_full_scan(repo_path)

    output_path = args.output
    if not output_path:
        repo_name = os.path.basename(repo_path)
        output_path = os.path.join(os.getcwd(), f"{repo_name}_health_report.json")

    json_content = format_json_report(report)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        print(Colors.green(f"JSON report saved to: {output_path}"))
    except OSError as e:
        print(Colors.red(f"Error writing report: {e}"))
        sys.exit(1)


def cmd_check(args: argparse.Namespace) -> None:
    """Handle the 'check' CLI command.

    Performs a quick check of critical items only.

    Args:
        args: Parsed command-line arguments with 'path' attribute.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_quick_check(repo_path)
    print(format_tui_report(report))


def cmd_history(args: argparse.Namespace) -> None:
    """Handle the 'history' CLI command.

    Performs detailed commit history analysis.

    Args:
        args: Parsed command-line arguments with 'path' attribute.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_history_analysis(repo_path)
    print(format_tui_report(report))


def cmd_deps(args: argparse.Namespace) -> None:
    """Handle the 'deps' CLI command.

    Performs dependency-focused analysis.

    Args:
        args: Parsed command-line arguments with 'path' attribute.
    """
    repo_path = resolve_repo_path(args.path)
    report = run_deps_analysis(repo_path)
    print(format_tui_report(report))


# =============================================================================
# CLI Entry Point
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI.

    Returns:
        A configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="repohealth",
        description="RepoHealth - Lightweight Git Repository Health Check Engine",
        epilog="Example: repohealth scan /path/to/repo",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--version", action="version",
        version="RepoHealth v1.0.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Full health scan")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    scan_parser.set_defaults(func=cmd_scan)

    # report command
    report_parser = subparsers.add_parser("report", help="Generate HTML report")
    report_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    report_parser.add_argument("-o", "--output", help="Output HTML file path")
    report_parser.set_defaults(func=cmd_report)

    # json command
    json_parser = subparsers.add_parser("json", help="Export JSON report")
    json_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    json_parser.add_argument("-o", "--output", help="Output JSON file path")
    json_parser.set_defaults(func=cmd_json)

    # check command
    check_parser = subparsers.add_parser("check", help="Quick check (critical items)")
    check_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    check_parser.set_defaults(func=cmd_check)

    # history command
    history_parser = subparsers.add_parser("history", help="Commit history analysis")
    history_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    history_parser.set_defaults(func=cmd_history)

    # deps command
    deps_parser = subparsers.add_parser("deps", help="Dependency analysis")
    deps_parser.add_argument("path", nargs="?", default=".", help="Path to repository")
    deps_parser.set_defaults(func=cmd_deps)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the RepoHealth CLI.

    Parses command-line arguments and dispatches to the appropriate
    command handler.

    Args:
        argv: Optional list of command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle color settings
    if getattr(args, "no_color", False):
        Colors.disable()
    else:
        Colors.auto()

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    func = getattr(args, "func", None)
    if func:
        try:
            func(args)
            return 0
        except KeyboardInterrupt:
            print(Colors.yellow("\nOperation cancelled."))
            return 130
        except Exception as e:
            print(Colors.red(f"Unexpected error: {e}"))
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
