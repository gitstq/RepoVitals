<div align="center">

# 🔬 RepoVitals

**轻量级 Git 仓库智能健康体检引擎 CLI**

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/gitstq/RepoVitals/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

[English](#english) | [简体中文](#简体中文) | [繁體中文](#繁體中文)

</div>

---

## 简体中文

### 🎉 项目介绍

RepoVitals 是一款专为开发者打造的 **轻量级 Git 仓库健康体检引擎**，以纯 Python 实现、零外部依赖为核心理念，帮助你在几秒钟内全面诊断仓库的健康状况。

**为什么需要 RepoVitals？**

- 🔍 **痛点一**：仓库日渐臃肿，却不知道哪些大文件在悄悄吞噬空间
- 📋 **痛点二**：团队提交规范混乱，Conventional Commits 形同虚设
- 🌿 **痛点三**：过期分支堆积如山，合并状态一团糟
- 🔒 **痛点四**：依赖库漏洞频发，却缺少自动化的版本审计手段
- 📖 **痛点五**：开源项目文档缺失，新贡献者望而却步

**自研差异化亮点：**

| 亮点 | 说明 |
|------|------|
| 🪶 **极致轻量** | 纯 Python 标准库实现，零 pip 依赖，即装即用 |
| 🎯 **10 维深度扫描** | 覆盖提交规范、分支健康、仓库大小、依赖安全等全方位检查 |
| 🖥️ **TUI 彩色输出** | 终端内直接呈现彩色表格，一目了然 |
| 📊 **多格式报告** | 支持 HTML 可视化报告与 JSON 结构化导出 |
| ⚡ **毫秒级响应** | 本地分析无网络请求，速度极快 |

---

### ✨ 核心特性

RepoVitals 提供 **10 大检查维度**，全方位守护你的仓库健康：

| # | 检查维度 | 说明 |
|---|----------|------|
| 📝 | **提交规范检查** | Conventional Commits 合规率分析，自动识别不规范提交 |
| 🌿 | **分支健康度** | 过期分支检测、长期未合并分支预警、合并状态分析 |
| 📦 | **仓库大小分析** | 大文件 TOP 榜、`.gitignore` 覆盖度评估 |
| 🔒 | **依赖安全扫描** | 支持 `requirements.txt`、`package.json`、`Pipfile` 等多格式版本检查 |
| 📖 | **文档完整度** | README / LICENSE / CONTRIBUTING / CHANGELOG 等关键文件检查 |
| 🧩 | **代码复杂度** | 函数长度统计、文件行数分布、复杂度热点定位 |
| 📊 | **Git 历史分析** | 提交频率趋势、贡献者分布、**Bus Factor** 风险评估 |
| 🛡️ | **安全基线检查** | 敏感文件检测（密钥、凭证）、硬编码密钥扫描 |
| ⚙️ | **CI/CD 配置检测** | GitHub Actions / GitLab CI / Jenkins / Travis CI 等多平台识别 |
| 🏷️ | **仓库元数据检查** | `description` / `topics` / `homepage` / `license` 等元数据完整性 |

---

### 🚀 快速开始

#### 📋 环境要求

- **Python** >= 3.8
- **Git** >= 2.0
- **操作系统**：Windows / macOS / Linux 全平台支持

#### 📥 安装方式

**方式一：通过 pip 直接安装（推荐）**

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

**方式二：克隆源码本地安装**

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals
pip install -e .
```

#### 🏃 快速体验

```bash
# 扫描当前目录，终端彩色表格输出
repovitals scan .

# 生成 HTML 可视化报告
repovitals report ./my-project -o health-report.html

# 导出 JSON 结构化报告
repovitals json ./my-project

# 仅检查关键项（快速模式）
repovitals check .

# 提交历史深度分析
repovitals history .

# 依赖安全分析
repovitals deps .
```

---

### 📖 详细使用指南

#### 🛠️ 命令一览

| 命令 | 功能 | 输出格式 |
|------|------|----------|
| `scan` | 完整扫描，TUI 彩色表格 | 终端表格 |
| `report` | 生成 HTML 可视化报告 | HTML 文件 |
| `json` | 导出 JSON 结构化报告 | JSON 文件 |
| `check` | 快速检查（仅关键项） | 终端摘要 |
| `history` | 提交历史分析 | 终端图表 |
| `deps` | 依赖分析 | 终端报告 |

#### 📌 进阶用法

**指定输出目录与文件名：**

```bash
repovitals report ./my-project -o ./reports/v2-health.html
```

**扫描远程仓库（需先克隆到本地）：**

```bash
git clone https://github.com/user/repo.git /tmp/repo
repovitals scan /tmp/repo
```

**组合使用——先快速检查再深度扫描：**

```bash
repovitals check . && repovitals report . -o full-report.html
```

#### 🎯 典型使用场景

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| 日常开发自检 | `repovitals check .` | 几秒内完成关键项检查 |
| 代码评审前 | `repovitals scan .` | 全面扫描，确保提交规范 |
| 开源项目维护 | `repovitals report . -o report.html` | 生成报告，展示项目健康度 |
| CI/CD 集成 | `repovitals json . --exit-code` | JSON 输出 + 退出码，便于流水线判断 |
| 依赖审计 | `repovitals deps .` | 定期检查依赖版本安全状态 |
| 团队贡献分析 | `repovitals history .` | 了解团队贡献分布和 Bus Factor |

---

### 💡 设计思路与迭代规划

#### 🧠 设计理念

RepoVitals 的核心设计哲学可以概括为三个关键词：

1. **轻量（Lightweight）** —— 不引入任何第三方依赖，全部基于 Python 标准库实现，确保在任何环境下都能零障碍运行。
2. **全面（Comprehensive）** —— 10 大检查维度覆盖仓库健康的方方面面，从代码规范到安全基线，一个工具搞定。
3. **友好（Developer-Friendly）** —— 彩色 TUI 输出、多格式报告导出、清晰的命令行接口，让体检结果一目了然。

#### 🔧 技术选型原因

| 决策 | 原因 |
|------|------|
| 纯 Python 实现 | 降低使用门槛，Python 开发者无需额外安装运行时 |
| 零外部依赖 | 避免依赖冲突，CI/CD 环境中即装即用 |
| CLI 工具形态 | 与 Git 工作流天然融合，方便脚本集成 |
| HTML 报告输出 | 无需额外服务，浏览器直接打开即可查看 |

#### 🗺️ 后续迭代计划

- [ ] 🔌 **插件系统**：支持自定义检查规则插件
- [ ] 📈 **趋势追踪**：多次扫描结果对比，健康度变化趋势图
- [ ] 🌐 **Web Dashboard**：本地启动 Web 面板，交互式查看报告
- [ ] 🔗 **远程仓库支持**：直接扫描 GitHub/GitLab 远程仓库（无需克隆）
- [ ] 📋 **PR 集成**：作为 GitHub Action / GitLab CI 在 PR 中自动评论体检结果
- [ ] 🎨 **自定义主题**：HTML 报告支持自定义样式主题

---

### 📦 打包与部署指南

#### 📦 pip 安装（推荐）

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

安装完成后，`repovitals` 命令将自动注册到系统 PATH 中。

#### 🔧 源码运行

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals

# 安装为可编辑模式
pip install -e .

# 或直接运行
python -m repohealth scan .
```

#### 🐍 虚拟环境建议

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install git+https://github.com/gitstq/RepoVitals.git
```

---

### 🤝 贡献指南

我们欢迎并感谢每一位贡献者！以下是参与贡献的基本流程：

#### 📝 提交 PR 规范

1. **Fork** 本仓库并创建你的特性分支：`git checkout -b feature/amazing-feature`
2. **提交** 你的改动，请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
   - `feat: 新增 XXX 功能`
   - `fix: 修复 XXX 问题`
   - `docs: 更新 XXX 文档`
   - `refactor: 重构 XXX 模块`
3. **推送** 到你的 Fork：`git push origin feature/amazing-feature`
4. 提交 **Pull Request**，并在 PR 描述中详细说明改动内容

#### 🐛 Issue 反馈规则

- 使用清晰的标题描述问题
- 附上复现步骤和期望行为
- 贴出相关日志或截图
- 标注适用的标签（`bug` / `feature` / `question`）

---

### 📄 开源协议

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2024 RepoVitals Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**用 RepoVitals，给你的仓库做一次全面体检吧！** 🏥

Made with ❤️ by [RepoVitals Contributors](https://github.com/gitstq/RepoVitals/graphs/contributors)

</div>

---

## English

### 🎉 Introduction

RepoVitals is a **lightweight Git repository health check engine CLI** built with pure Python and zero external dependencies. It helps you comprehensively diagnose your repository's health in seconds.

**Why RepoVitals?**

- 🔍 **Pain Point 1**: Your repo keeps growing, but you don't know which large files are silently eating up space
- 📋 **Pain Point 2**: Team commit conventions are chaotic, and Conventional Commits is barely enforced
- 🌿 **Pain Point 3**: Stale branches pile up, and merge states are a mess
- 🔒 **Pain Point 4**: Dependency vulnerabilities keep surfacing, but you lack automated version auditing
- 📖 **Pain Point 5**: Open source project documentation is incomplete, driving away potential contributors

**Key Differentiators:**

| Feature | Description |
|---------|-------------|
| 🪶 **Ultra Lightweight** | Pure Python standard library, zero pip dependencies, install and run |
| 🎯 **10-Dimension Deep Scan** | Covers commit conventions, branch health, repo size, dependency security, and more |
| 🖥️ **TUI Color Output** | Beautiful colorized tables directly in your terminal |
| 📊 **Multi-Format Reports** | HTML visual reports and JSON structured exports |
| ⚡ **Millisecond Response** | Fully local analysis with no network requests |

---

### ✨ Core Features

RepoVitals provides **10 inspection dimensions** for comprehensive repository health coverage:

| # | Dimension | Description |
|---|-----------|-------------|
| 📝 | **Commit Convention Check** | Conventional Commits compliance analysis, auto-detect non-conforming commits |
| 🌿 | **Branch Health** | Stale branch detection, long-unmerged branch warnings, merge status analysis |
| 📦 | **Repository Size Analysis** | Large file TOP list, `.gitignore` coverage assessment |
| 🔒 | **Dependency Security Scan** | Multi-format version checking for `requirements.txt`, `package.json`, `Pipfile`, etc. |
| 📖 | **Documentation Completeness** | Key file checks for README / LICENSE / CONTRIBUTING / CHANGELOG |
| 🧩 | **Code Complexity** | Function length stats, file line distribution, complexity hotspot detection |
| 📊 | **Git History Analysis** | Commit frequency trends, contributor distribution, **Bus Factor** risk assessment |
| 🛡️ | **Security Baseline Check** | Sensitive file detection (keys, credentials), hardcoded secret scanning |
| ⚙️ | **CI/CD Configuration Detection** | Multi-platform recognition for GitHub Actions / GitLab CI / Jenkins / Travis CI |
| 🏷️ | **Repository Metadata Check** | Completeness of `description` / `topics` / `homepage` / `license` metadata |

---

### 🚀 Quick Start

#### 📋 Prerequisites

- **Python** >= 3.8
- **Git** >= 2.0
- **OS**: Windows / macOS / Linux

#### 📥 Installation

**Option 1: Install via pip (Recommended)**

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

**Option 2: Clone and install locally**

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals
pip install -e .
```

#### 🏃 Quick Demo

```bash
# Full scan with colorized TUI table
repovitals scan .

# Generate HTML visual report
repovitals report ./my-project -o health-report.html

# Export JSON structured report
repovitals json ./my-project

# Quick check (critical items only)
repovitals check .

# Commit history deep analysis
repovitals history .

# Dependency analysis
repovitals deps .
```

---

### 📖 Detailed Usage Guide

#### 🛠️ Command Reference

| Command | Function | Output Format |
|---------|----------|---------------|
| `scan` | Full scan with TUI colorized table | Terminal table |
| `report` | Generate HTML visual report | HTML file |
| `json` | Export JSON structured report | JSON file |
| `check` | Quick check (critical items only) | Terminal summary |
| `history` | Commit history analysis | Terminal chart |
| `deps` | Dependency analysis | Terminal report |

#### 📌 Advanced Usage

**Specify output directory and filename:**

```bash
repovitals report ./my-project -o ./reports/v2-health.html
```

**Scan a remote repository (clone first):**

```bash
git clone https://github.com/user/repo.git /tmp/repo
repovitals scan /tmp/repo
```

**Combine commands — quick check first, then deep scan:**

```bash
repovitals check . && repovitals report . -o full-report.html
```

#### 🎯 Typical Use Cases

| Scenario | Recommended Command | Description |
|----------|---------------------|-------------|
| Daily dev self-check | `repovitals check .` | Critical items check in seconds |
| Pre-code review | `repovitals scan .` | Full scan to ensure commit conventions |
| Open source maintenance | `repovitals report . -o report.html` | Generate report to showcase project health |
| CI/CD integration | `repovitals json . --exit-code` | JSON output + exit code for pipeline gating |
| Dependency audit | `repovitals deps .` | Regular dependency version security check |
| Team contribution analysis | `repovitals history .` | Understand team contribution distribution and Bus Factor |

---

### 💡 Design Philosophy & Roadmap

#### 🧠 Design Philosophy

RepoVitals' core design philosophy can be summarized in three keywords:

1. **Lightweight** — No third-party dependencies at all. Everything is built on the Python standard library, ensuring zero-barrier execution in any environment.
2. **Comprehensive** — 10 inspection dimensions cover every aspect of repository health, from code conventions to security baselines, all in one tool.
3. **Developer-Friendly** — Colorized TUI output, multi-format report exports, and a clean CLI interface make health check results clear at a glance.

#### 🔧 Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Pure Python | Lowers the barrier to entry; Python developers don't need additional runtimes |
| Zero external dependencies | Avoids dependency conflicts; install-and-run in CI/CD environments |
| CLI tool form | Naturally integrates with Git workflows; easy to script |
| HTML report output | No extra services needed; just open in a browser |

#### 🗺️ Roadmap

- [ ] 🔌 **Plugin System**: Support custom inspection rule plugins
- [ ] 📈 **Trend Tracking**: Compare multiple scan results with health trend charts
- [ ] 🌐 **Web Dashboard**: Launch a local web panel for interactive report viewing
- [ ] 🔗 **Remote Repository Support**: Scan GitHub/GitLab remote repos directly (no clone needed)
- [ ] 📋 **PR Integration**: Auto-comment health check results in PRs via GitHub Action / GitLab CI
- [ ] 🎨 **Custom Themes**: Customizable style themes for HTML reports

---

### 📦 Packaging & Deployment Guide

#### 📦 pip Install (Recommended)

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

After installation, the `repovitals` command will be automatically registered in your system PATH.

#### 🔧 Run from Source

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals

# Install in editable mode
pip install -e .

# Or run directly
python -m repohealth scan .
```

#### 🐍 Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install git+https://github.com/gitstq/RepoVitals.git
```

---

### 🤝 Contributing Guide

We welcome and appreciate every contributor! Here's the basic workflow:

#### 📝 PR Submission Guidelines

1. **Fork** this repo and create your feature branch: `git checkout -b feature/amazing-feature`
2. **Commit** your changes following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add XXX feature`
   - `fix: resolve XXX issue`
   - `docs: update XXX documentation`
   - `refactor: refactor XXX module`
3. **Push** to your fork: `git push origin feature/amazing-feature`
4. Submit a **Pull Request** with a detailed description of your changes

#### 🐛 Issue Reporting Guidelines

- Use a clear title to describe the issue
- Include reproduction steps and expected behavior
- Attach relevant logs or screenshots
- Apply appropriate labels (`bug` / `feature` / `question`)

---

### 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

```
MIT License

Copyright (c) 2024 RepoVitals Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**Give your repository a comprehensive health check with RepoVitals!** 🏥

Made with ❤️ by [RepoVitals Contributors](https://github.com/gitstq/RepoVitals/graphs/contributors)

</div>

---

## 繁體中文

### 🎉 專案介紹

RepoVitals 是一款專為開發者打造的 **輕量級 Git 倉庫健康體檢引擎**，以純 Python 實現、零外部依賴為核心理念，幫助你在幾秒鐘內全面診斷倉庫的健康狀況。

**為什麼需要 RepoVitals？**

- 🔍 **痛點一**：倉庫日漸臃腫，卻不知道哪些大檔案在悄悄吞噬空間
- 📋 **痛點二**：團隊提交規範混亂，Conventional Commits 形同虛設
- 🌿 **痛點三**：過期分支堆積如山，合併狀態一團糟
- 🔒 **痛點四**：依賴庫漏洞頻發，卻缺少自動化的版本審計手段
- 📖 **痛點五**：開源專案文件缺失，新貢獻者望而卻步

**自研差異化亮點：**

| 亮點 | 說明 |
|------|------|
| 🪶 **極致輕量** | 純 Python 標準庫實現，零 pip 依賴，即裝即用 |
| 🎯 **10 維深度掃描** | 覆蓋提交規範、分支健康、倉庫大小、依賴安全等全方位檢查 |
| 🖥️ **TUI 彩色輸出** | 終端內直接呈現彩色表格，一目了然 |
| 📊 **多格式報告** | 支援 HTML 視覺化報告與 JSON 結構化匯出 |
| ⚡ **毫秒級回應** | 本地分析無網路請求，速度極快 |

---

### ✨ 核心特性

RepoVitals 提供 **10 大檢查維度**，全方位守護你的倉庫健康：

| # | 檢查維度 | 說明 |
|---|----------|------|
| 📝 | **提交規範檢查** | Conventional Commits 合規率分析，自動識別不規範提交 |
| 🌿 | **分支健康度** | 過期分支偵測、長期未合併分支預警、合併狀態分析 |
| 📦 | **倉庫大小分析** | 大檔案 TOP 榜、`.gitignore` 覆蓋度評估 |
| 🔒 | **依賴安全掃描** | 支援 `requirements.txt`、`package.json`、`Pipfile` 等多格式版本檢查 |
| 📖 | **文件完整度** | README / LICENSE / CONTRIBUTING / CHANGELOG 等關鍵檔案檢查 |
| 🧩 | **程式碼複雜度** | 函數長度統計、檔案行數分佈、複雜度熱點定位 |
| 📊 | **Git 歷史分析** | 提交頻率趨勢、貢獻者分佈、**Bus Factor** 風險評估 |
| 🛡️ | **安全基線檢查** | 敏感檔案偵測（金鑰、憑證）、硬編碼密鑰掃描 |
| ⚙️ | **CI/CD 配置偵測** | GitHub Actions / GitLab CI / Jenkins / Travis CI 等多平台識別 |
| 🏷️ | **倉庫元資料檢查** | `description` / `topics` / `homepage` / `license` 等元資料完整性 |

---

### 🚀 快速開始

#### 📋 環境需求

- **Python** >= 3.8
- **Git** >= 2.0
- **作業系統**：Windows / macOS / Linux 全平台支援

#### 📥 安裝方式

**方式一：透過 pip 直接安裝（推薦）**

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

**方式二：克隆原始碼本地安裝**

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals
pip install -e .
```

#### 🏃 快速體驗

```bash
# 掃描當前目錄，終端彩色表格輸出
repovitals scan .

# 生成 HTML 視覺化報告
repovitals report ./my-project -o health-report.html

# 匯出 JSON 結構化報告
repovitals json ./my-project

# 僅檢查關鍵項（快速模式）
repovitals check .

# 提交歷史深度分析
repovitals history .

# 依賴分析
repovitals deps .
```

---

### 📖 詳細使用指南

#### 🛠️ 命令一覽

| 命令 | 功能 | 輸出格式 |
|------|------|----------|
| `scan` | 完整掃描，TUI 彩色表格 | 終端表格 |
| `report` | 生成 HTML 視覺化報告 | HTML 檔案 |
| `json` | 匯出 JSON 結構化報告 | JSON 檔案 |
| `check` | 快速檢查（僅關鍵項） | 終端摘要 |
| `history` | 提交歷史分析 | 終端圖表 |
| `deps` | 依賴分析 | 終端報告 |

#### 📌 進階用法

**指定輸出目錄與檔案名稱：**

```bash
repovitals report ./my-project -o ./reports/v2-health.html
```

**掃描遠端倉庫（需先克隆到本地）：**

```bash
git clone https://github.com/user/repo.git /tmp/repo
repovitals scan /tmp/repo
```

**組合使用——先快速檢查再深度掃描：**

```bash
repovitals check . && repovitals report . -o full-report.html
```

#### 🎯 典型使用場景

| 場景 | 推薦命令 | 說明 |
|------|----------|------|
| 日常開發自檢 | `repovitals check .` | 幾秒內完成關鍵項檢查 |
| 程式碼審查前 | `repovitals scan .` | 全面掃描，確保提交規範 |
| 開源專案維護 | `repovitals report . -o report.html` | 生成報告，展示專案健康度 |
| CI/CD 整合 | `repovitals json . --exit-code` | JSON 輸出 + 退出碼，便於流水線判斷 |
| 依賴審計 | `repovitals deps .` | 定期檢查依賴版本安全狀態 |
| 團隊貢獻分析 | `repovitals history .` | 了解團隊貢獻分佈和 Bus Factor |

---

### 💡 設計思路與迭代規劃

#### 🧠 設計理念

RepoVitals 的核心設計哲學可以概括為三個關鍵詞：

1. **輕量（Lightweight）** —— 不引入任何第三方依賴，全部基於 Python 標準庫實現，確保在任何環境下都能零障礙運行。
2. **全面（Comprehensive）** —— 10 大檢查維度覆蓋倉庫健康的方方面面，從程式碼規範到安全基線，一個工具搞定。
3. **友善（Developer-Friendly）** —— 彩色 TUI 輸出、多格式報告匯出、清晰的命令列介面，讓體檢結果一目了然。

#### 🔧 技術選型原因

| 決策 | 原因 |
|------|------|
| 純 Python 實現 | 降低使用門檻，Python 開發者無需額外安裝執行環境 |
| 零外部依賴 | 避免依賴衝突，CI/CD 環境中即裝即用 |
| CLI 工具形態 | 與 Git 工作流程天然融合，方便腳本整合 |
| HTML 報告輸出 | 無需額外服務，瀏覽器直接開啟即可查看 |

#### 🗺️ 後續迭代計畫

- [ ] 🔌 **外掛系統**：支援自訂檢查規則外掛
- [ ] 📈 **趨勢追蹤**：多次掃描結果對比，健康度變化趨勢圖
- [ ] 🌐 **Web Dashboard**：本地啟動 Web 面板，互動式查看報告
- [ ] 🔗 **遠端倉庫支援**：直接掃描 GitHub/GitLab 遠端倉庫（無需克隆）
- [ ] 📋 **PR 整合**：作為 GitHub Action / GitLab CI 在 PR 中自動評論體檢結果
- [ ] 🎨 **自訂主題**：HTML 報告支援自訂樣式主題

---

### 📦 打包與部署指南

#### 📦 pip 安裝（推薦）

```bash
pip install git+https://github.com/gitstq/RepoVitals.git
```

安裝完成後，`repovitals` 命令將自動註冊到系統 PATH 中。

#### 🔧 原始碼運行

```bash
git clone https://github.com/gitstq/RepoVitals.git
cd RepoVitals

# 安裝為可編輯模式
pip install -e .

# 或直接運行
python -m repohealth scan .
```

#### 🐍 虛擬環境建議

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install git+https://github.com/gitstq/RepoVitals.git
```

---

### 🤝 貢獻指南

我們歡迎並感謝每一位貢獻者！以下是參與貢獻的基本流程：

#### 📝 提交 PR 規範

1. **Fork** 本倉庫並建立你的特性分支：`git checkout -b feature/amazing-feature`
2. **提交** 你的改動，請遵循 [Conventional Commits](https://www.conventionalcommits.org/) 規範：
   - `feat: 新增 XXX 功能`
   - `fix: 修復 XXX 問題`
   - `docs: 更新 XXX 文件`
   - `refactor: 重構 XXX 模組`
3. **推送** 到你的 Fork：`git push origin feature/amazing-feature`
4. 提交 **Pull Request**，並在 PR 描述中詳細說明改動內容

#### 🐛 Issue 回饋規則

- 使用清晰的標題描述問題
- 附上重現步驟和期望行為
- 貼出相關日誌或截圖
- 標註適用的標籤（`bug` / `feature` / `question`）

---

### 📄 開源協議

本專案基於 [MIT License](https://opensource.org/licenses/MIT) 開源。

```
MIT License

Copyright (c) 2024 RepoVitals Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**用 RepoVitals，給你的倉庫做一次全面體檢吧！** 🏥

Made with ❤️ by [RepoVitals Contributors](https://github.com/gitstq/RepoVitals/graphs/contributors)

</div>
