#!/usr/bin/env python3
"""Unit tests for RepoHealth.

Tests cover core utilities, check functions, and report formatters.
Uses only Python standard library (unittest + tempfile for test fixtures).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import repohealth
from repohealth import (
    Colors,
    CheckResult,
    HealthReport,
    check_conventional_commits,
    check_branch_health,
    check_repo_size,
    check_dependency_security,
    check_documentation,
    check_code_complexity,
    check_git_history,
    check_security_baseline,
    check_cicd_config,
    check_repo_metadata,
    format_tui_report,
    format_json_report,
    format_html_report,
    run_full_scan,
    run_quick_check,
    run_history_analysis,
    run_deps_analysis,
    build_parser,
    is_git_repo,
    resolve_repo_path,
    run_git,
    main,
)


class TestColors(unittest.TestCase):
    """Tests for the Colors ANSI utility class."""

    def setUp(self) -> None:
        """Reset color state before each test."""
        Colors.enable()

    def test_enable_disable(self) -> None:
        """Test color enable/disable functionality."""
        Colors.enable()
        self.assertTrue(Colors.is_enabled())
        Colors.disable()
        self.assertFalse(Colors.is_enabled())
        Colors.enable()

    def test_wrap_with_colors(self) -> None:
        """Test text wrapping with color codes."""
        result = Colors.wrap("hello", Colors.RED)
        self.assertIn("\033[31m", result)
        self.assertIn("hello", result)
        self.assertIn(Colors.RESET, result)

    def test_wrap_without_colors(self) -> None:
        """Test text wrapping returns plain text when colors disabled."""
        Colors.disable()
        result = Colors.wrap("hello", Colors.RED)
        self.assertEqual(result, "hello")
        Colors.enable()

    def test_color_methods(self) -> None:
        """Test individual color methods return ANSI codes."""
        self.assertIn("\033[31m", Colors.red("test"))
        self.assertIn("\033[32m", Colors.green("test"))
        self.assertIn("\033[33m", Colors.yellow("test"))
        self.assertIn("\033[34m", Colors.blue("test"))
        self.assertIn("\033[36m", Colors.cyan("test"))
        self.assertIn("\033[1m", Colors.bold("test"))

    def test_score_color(self) -> None:
        """Test score-based color selection."""
        self.assertEqual(Colors.score_color(90), Colors.GREEN)
        self.assertEqual(Colors.score_color(80), Colors.GREEN)
        self.assertEqual(Colors.score_color(70), Colors.YELLOW)
        self.assertEqual(Colors.score_color(50), Colors.RED)

    def test_auto_detect(self) -> None:
        """Test auto-detection of TTY."""
        # Should not raise
        Colors.auto()
        # Result depends on environment, just ensure no crash
        self.assertIsInstance(Colors.is_enabled(), bool)


class TestCheckResult(unittest.TestCase):
    """Tests for the CheckResult data class."""

    def test_default_values(self) -> None:
        """Test CheckResult default initialization."""
        result = CheckResult(name="Test", score=85.0)
        self.assertEqual(result.name, "Test")
        self.assertEqual(result.score, 85.0)
        self.assertEqual(result.weight, 1.0)
        self.assertEqual(result.details, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.errors, [])

    def test_to_dict(self) -> None:
        """Test CheckResult dictionary serialization."""
        result = CheckResult(name="Test", score=75.5, weight=0.8)
        result.details.append("detail1")
        result.warnings.append("warn1")
        d = result.to_dict()
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["score"], 75.5)
        self.assertEqual(d["weight"], 0.8)
        self.assertIn("detail1", d["details"])
        self.assertIn("warn1", d["warnings"])


class TestHealthReport(unittest.TestCase):
    """Tests for the HealthReport data class."""

    def test_calculate_total_empty(self) -> None:
        """Test total calculation with no results."""
        report = HealthReport(repo_path="/tmp", scan_time="now")
        self.assertEqual(report.calculate_total(), 0.0)

    def test_calculate_total_single(self) -> None:
        """Test total calculation with a single result."""
        report = HealthReport(repo_path="/tmp", scan_time="now")
        report.results.append(CheckResult(name="Test", score=80.0, weight=1.0))
        self.assertEqual(report.calculate_total(), 80.0)

    def test_calculate_total_weighted(self) -> None:
        """Test weighted total calculation."""
        report = HealthReport(repo_path="/tmp", scan_time="now")
        report.results.append(CheckResult(name="A", score=100.0, weight=2.0))
        report.results.append(CheckResult(name="B", score=50.0, weight=1.0))
        # (100*2 + 50*1) / (2+1) = 250/3 = 83.3
        total = report.calculate_total()
        self.assertAlmostEqual(total, 83.3, places=1)

    def test_to_dict(self) -> None:
        """Test HealthReport dictionary serialization."""
        report = HealthReport(repo_path="/tmp/test", scan_time="2025-01-01")
        report.results.append(CheckResult(name="Test", score=90.0))
        report.calculate_total()
        d = report.to_dict()
        self.assertEqual(d["repo_path"], "/tmp/test")
        self.assertEqual(d["total_score"], 90.0)
        self.assertEqual(len(d["results"]), 1)


class TestGitHelpers(unittest.TestCase):
    """Tests for git helper functions."""

    def test_is_git_repo_false(self) -> None:
        """Test is_git_repo returns False for non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(is_git_repo(tmpdir))

    def test_is_git_repo_true(self) -> None:
        """Test is_git_repo returns True for git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = os.path.join(tmpdir, ".git")
            os.makedirs(git_dir)
            self.assertTrue(is_git_repo(tmpdir))

    def test_run_git_not_found(self) -> None:
        """Test run_git handles missing git gracefully."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            rc, output = run_git("/tmp", "status")
            self.assertEqual(rc, -1)

    def test_run_git_success(self) -> None:
        """Test run_git returns output on success."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test output\n"
            mock_run.return_value = mock_result
            rc, output = run_git("/tmp", "status")
            self.assertEqual(rc, 0)
            self.assertEqual(output, "test output")


class TestConventionalCommits(unittest.TestCase):
    """Tests for conventional commits check."""

    def test_empty_repo(self) -> None:
        """Test check with empty repository (no commits)."""
        with patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_conventional_commits("/tmp")
            self.assertEqual(result.score, 100.0)

    def test_all_conventional(self) -> None:
        """Test check with all conventional commits."""
        log = "feat: add new feature\nfix: resolve bug\ndocs: update readme\n"
        with patch.object(repohealth, "run_git", return_value=(0, log)):
            result = check_conventional_commits("/tmp")
            self.assertEqual(result.score, 100.0)

    def test_none_conventional(self) -> None:
        """Test check with no conventional commits."""
        log = "updated stuff\nfixed that thing\nwip\n"
        with patch.object(repohealth, "run_git", return_value=(0, log)):
            result = check_conventional_commits("/tmp")
            self.assertLess(result.score, 50.0)

    def test_mixed_commits(self) -> None:
        """Test check with mixed conventional and non-conventional commits."""
        log = "feat: add feature\nrandom commit\nfix: bug\nanother random\n"
        with patch.object(repohealth, "run_git", return_value=(0, log)):
            result = check_conventional_commits("/tmp")
            self.assertGreater(result.score, 0)
            self.assertLess(result.score, 100)


class TestDocumentation(unittest.TestCase):
    """Tests for documentation completeness check."""

    def test_no_docs(self) -> None:
        """Test check with no documentation files."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_documentation(tmpdir)
            self.assertLess(result.score, 50.0)
            self.assertTrue(any("README" in e for e in result.errors))

    def test_with_readme_and_license(self) -> None:
        """Test check with README and LICENSE present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create README and LICENSE
            readme_path = os.path.join(tmpdir, "README.md")
            with open(readme_path, "w") as f:
                f.write("# Test Project\n\n## Installation\n\npip install .\n\n## Usage\n\nUse it.\n\n## License\n\nMIT\n")
            license_path = os.path.join(tmpdir, "LICENSE")
            with open(license_path, "w") as f:
                f.write("MIT License\n")

            with patch.object(repohealth, "run_git", return_value=(0, "")):
                result = check_documentation(tmpdir)
                self.assertGreaterEqual(result.score, 45.0)


class TestSecurityBaseline(unittest.TestCase):
    """Tests for security baseline check."""

    def test_clean_repo(self) -> None:
        """Test check with no security issues."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "main.py\n")):
            # Create a clean Python file
            py_file = os.path.join(tmpdir, "main.py")
            with open(py_file, "w") as f:
                f.write("# Clean file\nprint('hello')\n")
            result = check_security_baseline(tmpdir)
            self.assertGreater(result.score, 80.0)

    def test_sensitive_file_detected(self) -> None:
        """Test check detects sensitive files."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, ".env\nmain.py\n")):
            # Create a .env file
            env_file = os.path.join(tmpdir, ".env")
            with open(env_file, "w") as f:
                f.write("SECRET_KEY=abc123\n")
            py_file = os.path.join(tmpdir, "main.py")
            with open(py_file, "w") as f:
                f.write("print('hello')\n")
            result = check_security_baseline(tmpdir)
            self.assertLess(result.score, 100.0)
            self.assertTrue(len(result.errors) > 0)

    def test_hardcoded_secret(self) -> None:
        """Test check detects hardcoded secrets."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "config.py\n")):
            # Create a file with hardcoded secret
            py_file = os.path.join(tmpdir, "config.py")
            with open(py_file, "w") as f:
                f.write("API_KEY = 'sk-1234567890abcdef'\n")
            result = check_security_baseline(tmpdir)
            self.assertLess(result.score, 100.0)


class TestCICDConfig(unittest.TestCase):
    """Tests for CI/CD configuration check."""

    def test_no_cicd(self) -> None:
        """Test check with no CI/CD configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_cicd_config(tmpdir)
            self.assertEqual(result.score, 20.0)
            self.assertTrue(any("No CI/CD" in w for w in result.warnings))

    def test_github_actions(self) -> None:
        """Test check detects GitHub Actions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = os.path.join(tmpdir, ".github", "workflows")
            os.makedirs(workflows_dir)
            workflow_file = os.path.join(workflows_dir, "ci.yml")
            with open(workflow_file, "w") as f:
                f.write("name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n")
            result = check_cicd_config(tmpdir)
            self.assertGreater(result.score, 40.0)


class TestDependencySecurity(unittest.TestCase):
    """Tests for dependency security check."""

    def test_no_deps(self) -> None:
        """Test check with no dependency files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_dependency_security(tmpdir)
            self.assertEqual(result.score, 100.0)

    def test_pinned_requirements(self) -> None:
        """Test check with pinned requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = os.path.join(tmpdir, "requirements.txt")
            with open(req_file, "w") as f:
                f.write("requests==2.28.0\nflask==2.2.0\nnumpy==1.23.0\n")
            result = check_dependency_security(tmpdir)
            self.assertGreater(result.score, 80.0)

    def test_unpinned_requirements(self) -> None:
        """Test check with unpinned requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = os.path.join(tmpdir, "requirements.txt")
            with open(req_file, "w") as f:
                f.write("requests\nflask\nnumpy\n")
            result = check_dependency_security(tmpdir)
            self.assertLess(result.score, 60.0)


class TestRepoSize(unittest.TestCase):
    """Tests for repository size check."""

    def test_empty_repo(self) -> None:
        """Test check with empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_repo_size(tmpdir)
            self.assertGreaterEqual(result.score, 80.0)

    def test_missing_gitignore(self) -> None:
        """Test check penalizes missing .gitignore."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "main.py\n")):
            py_file = os.path.join(tmpdir, "main.py")
            with open(py_file, "w") as f:
                f.write("print('hello')\n")
            result = check_repo_size(tmpdir)
            self.assertTrue(any(".gitignore" in e for e in result.errors))


class TestBranchHealth(unittest.TestCase):
    """Tests for branch health check."""

    def test_no_branches(self) -> None:
        """Test check with no branches."""
        with patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_branch_health("/tmp")
            self.assertEqual(result.score, 100.0)


class TestCodeComplexity(unittest.TestCase):
    """Tests for code complexity check."""

    def test_no_files(self) -> None:
        """Test check with no tracked files."""
        with patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_code_complexity("/tmp")
            self.assertEqual(result.score, 100.0)


class TestGitHistory(unittest.TestCase):
    """Tests for git history analysis check."""

    def test_no_commits(self) -> None:
        """Test check with no commits."""
        with patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_git_history("/tmp")
            self.assertEqual(result.score, 50.0)


class TestRepoMetadata(unittest.TestCase):
    """Tests for repository metadata check."""

    def test_empty_repo(self) -> None:
        """Test check with empty repository."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(repohealth, "run_git", return_value=(0, "")):
            result = check_repo_metadata(tmpdir)
            self.assertGreaterEqual(result.score, 0)
            self.assertLessEqual(result.score, 100)


class TestReportFormatters(unittest.TestCase):
    """Tests for report formatting functions."""

    def _make_sample_report(self) -> HealthReport:
        """Create a sample health report for testing.

        Returns:
            A HealthReport with sample data.
        """
        report = HealthReport(
            repo_path="/tmp/test_repo",
            scan_time="2025-01-01T12:00:00",
        )
        report.results.append(CheckResult(name="Test Check 1", score=90.0, weight=1.0))
        report.results.append(CheckResult(name="Test Check 2", score=50.0, weight=0.5))
        report.results[0].details.append("Detail for check 1")
        report.results[1].warnings.append("Warning for check 2")
        report.calculate_total()
        return report

    def test_tui_report(self) -> None:
        """Test TUI report generation."""
        report = self._make_sample_report()
        output = format_tui_report(report)
        self.assertIn("RepoHealth", output)
        self.assertIn("Test Check 1", output)
        self.assertIn("Test Check 2", output)
        self.assertIn("90.0", output)
        self.assertIn("50.0", output)

    def test_tui_report_no_color(self) -> None:
        """Test TUI report with colors disabled."""
        Colors.disable()
        report = self._make_sample_report()
        output = format_tui_report(report)
        self.assertNotIn("\033", output)
        Colors.enable()

    def test_json_report(self) -> None:
        """Test JSON report generation."""
        report = self._make_sample_report()
        output = format_json_report(report)
        data = json.loads(output)
        self.assertEqual(data["repo_path"], "/tmp/test_repo")
        self.assertEqual(data["total_score"], report.total_score)
        self.assertEqual(len(data["results"]), 2)

    def test_html_report(self) -> None:
        """Test HTML report generation."""
        report = self._make_sample_report()
        output = format_html_report(report)
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("RepoHealth", output)
        self.assertIn("Test Check 1", output)
        self.assertIn("</html>", output)
        # Check for embedded CSS
        self.assertIn("<style>", output)


class TestCLI(unittest.TestCase):
    """Tests for CLI argument parsing."""

    def test_build_parser(self) -> None:
        """Test parser creation."""
        parser = build_parser()
        self.assertIsNotNone(parser)

    def test_parse_scan_command(self) -> None:
        """Test parsing scan command."""
        parser = build_parser()
        args = parser.parse_args(["scan", "/tmp/repo"])
        self.assertEqual(args.command, "scan")
        self.assertEqual(args.path, "/tmp/repo")

    def test_parse_report_command(self) -> None:
        """Test parsing report command with output."""
        parser = build_parser()
        args = parser.parse_args(["report", "/tmp/repo", "-o", "report.html"])
        self.assertEqual(args.command, "report")
        self.assertEqual(args.output, "report.html")

    def test_parse_json_command(self) -> None:
        """Test parsing json command."""
        parser = build_parser()
        args = parser.parse_args(["json", "/tmp/repo"])
        self.assertEqual(args.command, "json")

    def test_parse_check_command(self) -> None:
        """Test parsing check command."""
        parser = build_parser()
        args = parser.parse_args(["check", "/tmp/repo"])
        self.assertEqual(args.command, "check")

    def test_parse_history_command(self) -> None:
        """Test parsing history command."""
        parser = build_parser()
        args = parser.parse_args(["history", "/tmp/repo"])
        self.assertEqual(args.command, "history")

    def test_parse_deps_command(self) -> None:
        """Test parsing deps command."""
        parser = build_parser()
        args = parser.parse_args(["deps", "/tmp/repo"])
        self.assertEqual(args.command, "deps")

    def test_default_path(self) -> None:
        """Test default path is current directory."""
        parser = build_parser()
        args = parser.parse_args(["scan"])
        self.assertEqual(args.path, ".")

    def test_no_color_flag(self) -> None:
        """Test --no-color flag."""
        parser = build_parser()
        args = parser.parse_args(["--no-color", "scan"])
        self.assertTrue(args.no_color)

    def test_main_no_args(self) -> None:
        """Test main with no arguments returns 0."""
        ret = main([])
        self.assertEqual(ret, 0)


class TestScanEngine(unittest.TestCase):
    """Tests for the scan engine functions."""

    def test_run_full_scan(self) -> None:
        """Test full scan execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            # Create some files
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Test\n")
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("print('hello')\n")
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.name=test", "-c", "user.email=test@test.com",
                 "commit", "-m", "feat: initial commit"],
                cwd=tmpdir, capture_output=True,
            )

            report = run_full_scan(tmpdir)
            self.assertGreater(len(report.results), 0)
            self.assertGreaterEqual(report.total_score, 0)
            self.assertLessEqual(report.total_score, 100)

    def test_run_quick_check(self) -> None:
        """Test quick check execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            report = run_quick_check(tmpdir)
            self.assertEqual(len(report.results), 3)

    def test_run_history_analysis(self) -> None:
        """Test history analysis execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            report = run_history_analysis(tmpdir)
            self.assertEqual(len(report.results), 2)

    def test_run_deps_analysis(self) -> None:
        """Test dependency analysis execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            report = run_deps_analysis(tmpdir)
            self.assertEqual(len(report.results), 1)


class TestGetScoreColor(unittest.TestCase):
    """Tests for the get_score_color helper function."""

    def test_green_score(self) -> None:
        """Test high score returns green color."""
        self.assertEqual(repohealth.get_score_color(90), "#3fb950")

    def test_yellow_score(self) -> None:
        """Test medium score returns yellow color."""
        self.assertEqual(repohealth.get_score_color(70), "#d29922")

    def test_red_score(self) -> None:
        """Test low score returns red color."""
        self.assertEqual(repohealth.get_score_color(40), "#f85149")


if __name__ == "__main__":
    unittest.main()
