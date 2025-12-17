# 项目文档索引（godotgame）

> 最后更新：2025-12-16  
> 项目定位：Godot 4.5 + C#/.NET 8（Windows-only）开箱即用模板  
> 迁移说明：本仓库已完成从旧项目到 Godot 模板的迁移；当前运行时不包含旧 Web 前端栈与旧桌面壳依赖。迁移历史材料在 `docs/migration/**`，仅用于历史对照。

---

## Quick Links（先看这些）

- 项目总览与一键命令：`../README.md`
- AI/协作规则（SSoT）：`../CLAUDE.md`、`../AGENTS.md`
- Godot+C# 快速开始（本仓模板）：`docs/TEMPLATE_GODOT_GETTING_STARTED.md`
- 测试框架与门禁说明：`docs/testing-framework.md`
- 文档导航（Base 骨干）：`docs/architecture/base/00-README.md`
- Release/CI 工作流说明（含 Sentry 软门禁）：`docs/workflows/GM-NG-T2-playable-guide.md`

---

## 1) 入口文档（SSoT）

- `../README.md`：模板简介、Quick Links、常用命令
- `../CLAUDE.md`：单一真相（AI 助手/架构/门禁/日志规范）
- `../AGENTS.md`：协作与编码规范（Windows only、UTF-8、日志与取证）

---

## 2) Getting Started（开始开发）

- `docs/TEMPLATE_GODOT_GETTING_STARTED.md`：从 0 到可跑/可测/可导出
- `docs/testing-framework.md`：xUnit + GdUnit4 + 覆盖率/门禁（Windows）

---

## 3) 架构文档（Base-Clean，arc42 12 章）

目录：`docs/architecture/base/`

- `docs/architecture/base/00-README.md`：Base 导航与维护说明
- `docs/architecture/base/01-introduction-and-goals-v2.md`：约束与目标（Godot+C# 口径）
- `docs/architecture/base/02-security-baseline-godot-v2.md`：安全基线（Godot 运行时）
- `docs/architecture/base/03-observability-sentry-logging-v2.md`：可观测性与 Release Health（Sentry）
- `docs/architecture/base/04-system-context-c4-event-flows-v2.md`：系统上下文、容器与事件流（Signals/Contracts）
- `docs/architecture/base/05-data-models-and-storage-ports-v2.md`：数据模型与存储端口
- `docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md`：运行时视图与状态机/错误路径
- `docs/architecture/base/07-dev-build-and-gates-v2.md`：开发/构建/质量门禁（Windows）
- `docs/architecture/base/08-crosscutting-and-feature-slices.base.md`：08 章模板（Base 禁止具体纵切）
- `docs/architecture/base/09-performance-and-capacity-v2.md`：性能与容量（帧时间 P95 门禁）
- `docs/architecture/base/10-i18n-ops-release-v2.md`：i18n 与发布运维（Windows-only）
- `docs/architecture/base/11-risks-and-technical-debt-v2.md`：风险与技术债
- `docs/architecture/base/12-glossary-v2.md`：术语表

---

## 4) ADR（架构决策记录）

目录：`docs/adr/`

- `docs/architecture/ADR_INDEX_GODOT.md`：当前 Godot 模板口径的 ADR 索引（Accepted + Addenda）
- `docs/adr/guide.md`：ADR 编写指南

---

## 5) Workflows（CI/协作手册）

目录：`docs/workflows/`

- `docs/workflows/GM-NG-T2-playable-guide.md`：可玩度/Release 工作流与 Sentry 软门禁说明
- `docs/workflows/doc-stack-convergence-guide.md`：文档口径全量收敛（Base/Migration 扫描、取证与验证）
- `docs/workflows/serena-mcp-command-reference.md`：Serena / Codex CLI 常用命令
- `docs/workflows/superclaude-command-reference.md`：SuperClaude 工作流说明
- `docs/workflows/task-master-superclaude-integration.md`：Taskmaster + SuperClaude 集成（如仅做 Godot 桌面模板，可先跳过 Web/旧桌面壳 相关段落）

---

## 6) Migration（历史对照与资料库）

目录：`docs/migration/`（包含从旧栈迁移到 Godot 的过程性材料；不作为当前运行时口径的唯一来源）

- `docs/migration/MIGRATION_INDEX.md`
- `docs/migration/Phase-12-Headless-Smoke-Tests.md`
- `docs/migration/Phase-17-Windows-Only-Quickstart.md`
- `docs/migration/Phase-17-Export-Checklist.md`
- `docs/migration/Phase-18-Staged-Release-and-Canary-Strategy.md`

---

## 7) Scripts & CI（可执行入口）

### PowerShell（Windows）

- `scripts/ci/quality_gate.ps1`：一键门禁入口（调用 Python gates，可选导出/冒烟/性能门禁）
- `scripts/ci/smoke_headless.ps1`：Godot headless 冒烟（产出 `logs/ci/**`）
- `scripts/ci/export_windows.ps1`：导出 Windows EXE
- `scripts/ci/check_perf_budget.ps1`：解析 `[PERF]` 标记并做 P95 门禁
- `scripts/ci/verify_base_clean.ps1`：Base-Clean 校验（禁止 Base 出现 PRD-ID/具体 08 内容）

### Python（py -3）

- `scripts/python/quality_gates.py`：本地/CI 统一门禁编排（dotnet + gdunit + encoding 等）
- `scripts/python/check_sentry_secrets.py`：Sentry Secrets 软门禁（Step Summary）
- `scripts/python/check_encoding.py`：UTF-8/疑似乱码扫描（写入 `logs/ci/<YYYY-MM-DD>/encoding/**`）
- `scripts/python/scan_doc_stack_terms.py`：旧技术栈术语扫描（用于文档收敛取证）
- `scripts/python/task_links_validate.py`：NG/GM ↔ ADR/章节/Overlay 回链校验（CI 门禁）
- `scripts/python/verify_task_mapping.py`：抽样检查任务映射元数据完整度（软检查）
- `scripts/python/validate_task_master_triplet.py`：三份任务文件结构总检（本地/后续 CI）
- `scripts/python/prd_coverage_report.py`：PRD→任务覆盖报表（软检查）

---

## 8) 日志与工件（排障入口）

- 统一目录：`logs/**`（单元/引擎冒烟/CI/性能/审计）
- 建议先看：`logs/ci/<YYYY-MM-DD>/`（门禁与扫描报告）
