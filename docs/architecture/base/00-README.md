# Base-Clean 概览与索引（非 SSoT）

本文件用于人工阅读与导航，帮助快速理解 Base-Clean 文档集的意图、组成与维护方式。

重要：本文件不是权威索引（SSoT）。机器可读的唯一权威索引为：

- 根目录：`architecture_base.index`（路径清单；供脚本消费）
- 人类友好索引（JSONL）：`docs/index/architecture_base.index`（title=FM 英文；displayTitle=正文首个 H1）

建议的维护与校验流程（Windows only）

- 快速入口：FeatureFlags Quickstart → `docs/migration/Phase-18-Staged-Release-and-Canary-Strategy.md`

- 变更章节内容后：
  1. 重建索引：`npm run docs:index:rebuild`
  2. 基线门禁：`npm run guard:base`（含编码扫描、索引一致性、ADR 引用扫描）
- ADR 引用同步（PRD 分片）：`npm run prd:adr:sync`（补 ADR‑0011、移 ADR‑0009、并扫描校验）
- 指南文档：`docs/adr/guide.md`

## 目标与边界（arc42 Base 骨干）

- Base 目录承载跨切面与系统骨干（arc42 §01–07、09–12），不包含任何具体 PRD 内容；08 章仅保留"功能纵切"模板（示例/约束）。
- 文中仅使用占位符 `${DOMAIN_*}` `${PRODUCT_*}` `${PRD_ID}` 等；不得出现真实域、仓库、具体 PRD 标识等。
- 与 ADR 对齐：任何落地性改动需引用已 Accepted 的 ADR；阈值/契约变化需新增或 Supersede。

## 章节导航（自动生成）

- 01 约束与目标（v2 骨架）- arc42 §1 对齐版本：`docs/architecture/base/01-introduction-and-goals-v2.md`
- 02 安全基线（Electron）v2 - 深度防御体系：`docs/architecture/base/02-security-baseline-electron-v2.md`
- .github/workflows/release-health-gate.yml：`docs/architecture/base/03-observability-sentry-logging-v2.md`
- 04 system context c4 event flows v2：`docs/architecture/base/04-system-context-c4-event-flows-v2.md`
- scripts/migration/run_migrations.mjs：`docs/architecture/base/05-data-models-and-storage-ports-v2.md`
- 06 runtime view loops state machines error paths v2：`docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md`
- Node-first 聚合示例（建议在 CI 与本地统一使用）：`docs/architecture/base/07-dev-build-and-gates-v2.md`
- 08 crosscutting and feature slices.base：`docs/architecture/base/08-crosscutting-and-feature-slices.base.md`
- .github/workflows/performance-gate.yml：`docs/architecture/base/09-performance-and-capacity-v2.md`
- .github/workflows/release.yml（摘要）：`docs/architecture/base/10-i18n-ops-release-v2.md`
- .env.risk-assessment：`docs/architecture/base/11-risks-and-technical-debt-v2.md`
- 12 glossary v2：`docs/architecture/base/12-glossary-v2.md`

参考文件（Base 目录内）

- `architecture-completeness-checklist.md`
- `csp-policy-analysis.md`
- `front-matter-standardization-example.md`

## Godot + C# 迁移口径（对齐 ADR-0018/0019）

- 技术栈与三层结构
  - 技术栈：Godot 4.5 + C#/.NET 8（见 ADR-0018）。
  - 结构：Scenes（装配/信号）→ Adapters（仅封装 Godot API）→ Core（纯 C# 领域，可单测）。
  - 当前仓库路径映射：Core → `Game.Core`；Adapters → `Game.Godot`；Scenes → 工程根下 `.tscn` 资源；场景测试 → `Tests.Godot`；领域测试将于 Phase 4 恢复为 xUnit。
- 安全基线
  - 本目录新增 `02-security-baseline-godot-v2.md` 作为运行时基线（引用 ADR-0019），替代 Electron 版本的 02 章作为执行口径。
- 契约 SSoT
  - 契约与事件仅落盘 `Scripts/Core/Contracts/**`（不依赖 Godot，不直接参与编译），各章节/用例引用路径，避免口径漂移。

## ADR 对齐（当前口径快照，自动生成）

- Accepted：ADR-0001 / ADR-0002 / ADR-0003 / ADR-0004 / ADR-0005 / ADR-0006 / ADR-0007 / ADR-0008 / ADR-0010 / ADR-0011 / ADR-0015
- Superseded：ADR-0009
- Proposed：（无）

提示：任何引用/删除/新增 ADR 后，请执行 `npm run prd:adr:sync` 与 `npm run guard:base` 确认无“未知/被替代”引用。

## 与 CI 的关系（Release Health & Perf）

- e2e perf smoke：在 CI 的"Build & Test / CI/CD Pipeline"使用软门禁（P95 阈值、预热、样本数、裁剪比由 perf-env 提供）；夜间/专项工作流保留硬门禁并增加样本以降低误判。
- 观测数据：Sentry Releases + Sessions 需启用以监控 Crash‑free 指标，未达阈值不得放量。

## 注意事项（防漂移）

- SSoT 始终以根目录 `architecture_base.index` 为准；本文件仅用于人工阅读，若与 SSoT 不一致，以 SSoT 为准。
- 统一用 TypeScript/ESM；Electron 安全基线：`nodeIntegration=false`、`contextIsolation=true`、严格 CSP。
- 任何“看起来像索引”的文件（含本文件）都不得被脚本消费为权威数据源。
## ADR Index (Godot Migration)

- [ADR-0018: Godot Runtime and Distribution](../../adr/ADR-0018-godot-runtime-and-distribution.md)
- [ADR-0019: Godot Security Baseline](../../adr/ADR-0019-godot-security-baseline.md)
- [ADR-0020: Godot Test Strategy (TDD + GdUnit4)](../../adr/ADR-0020-godot-test-strategy.md)
- [ADR-0021: C# Domain Layer Architecture](../../adr/ADR-0021-csharp-domain-layer-architecture.md)
- [ADR-0022: Godot Signal System and Contracts](../../adr/ADR-0022-godot-signal-system-and-contracts.md)

Addenda
- [ADR-0005 Addendum — Quality Gates for Godot+C#](../../adr/addenda/ADR-0005-godot-quality-gates-addendum.md)
- [ADR-0006 Addendum — Data Storage for Godot](../../adr/addenda/ADR-0006-godot-data-storage-addendum.md)
- [ADR-0015 Addendum — Performance Budgets for Godot](../../adr/addenda/ADR-0015-godot-performance-budgets-addendum.md)
