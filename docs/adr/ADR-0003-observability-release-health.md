---
ADR-ID: ADR-0003
title: 可观测性与 Release Health 策略（Sentry 集成）
status: Accepted
decision-time: '2025-08-24'
deciders: [架构团队, SRE团队]
archRefs: [CH01, CH03, CH07]
verification:
  - path: .release-health.json
    assert: 定义 CrashFreeUsers/CrashFreeSessions/minAdoption/noRegression 等阈值
  - path: scripts/release-health-gate.mjs
    assert: 阈值不达标时构建失败（Fail Fast）
  - path: scripts/telemetry/self-check.mjs
    assert: 会话遥测启用且在主进程与渲染进程尽早初始化
impact-scope: [src/shared/observability/, .release-health.json, scripts/]
tech-tags: [sentry, logging, monitoring, release-health, observability]
depends-on: []
depended-by: [ADR-0005, ADR-0008]
test-coverage: tests/unit/observability/sentry.spec.ts
monitoring-metrics:
  [crash_free_sessions, crash_free_users, error_rate, release_adoption]
executable-deliverables:
  - .release-health.json
  - src/shared/observability/sentry-config.ts
  - scripts/release-health-gate.mjs
supersedes: []
---

# ADR-0003: 可观测性与 Release Health 策略

## Context

需要一套统一的可观测性与发布健康（Release Health）机制：在 Electron 主进程与每个渲染进程尽早初始化 Sentry，启用会话跟踪、错误采集与结构化日志，使用 Crash‑Free Users/Sessions 作为发布门禁的核心指标；同时满足隐私合规与 Windows-only 仓库的运行规范（日志统一落盘 `logs/`）。

**重要术语澄清**：

- **Release Health Gate（本 ADR 范围）**：基于 Sentry Sessions/Users 的 Crash-Free 指标进行发布健康评估（如 24h ≥ 99.5%），属于可观测性与崩溃监控范畴。数据源为 Sentry SDK 自动收集的会话数据。
- **Gameplay Telemetry Gate（已移除）**：曾基于游戏内自定义埋点事件（如 first_build、first_wave 等）衡量可玩度与会话质量的门禁，依赖本地 SQLite/JSON 存储。该实现已于 2025 年完全移除（`electron/telemetry/**`、`scripts/export-telemetry-metrics.mjs`），替代方案为 T2 Playable E2E + 性能基线 Gate（见 ADR-0005）。

## Decision

- Sentry 集成：
  - 主进程与每个渲染进程在最早入口初始化；启用自动会话跟踪与必要的错误过滤。
  - 结构化日志与 PII 清洗在 SDK 层优先处理；必要时在服务端策略补充。
- Release Health 门禁：
  - 指标阈值在 `.release-health.json` 定义；CI 中由 `scripts/release-health-gate.mjs` 校验。
  - 最小采样数（adoption）必须满足后再评估 Crash‑Free 指标。
- Windows-only 工作流约束：
  - 所有构建/测试 Job 运行于 `windows-latest` 且 `pwsh`，日志输出统一落盘 `logs/YYYYMMDD/<module>/`。

### 文档链路宽松（DOCS_ONLY）与发布链路严格禁止

- 仅在“文档构建链路”允许 `DOCS_ONLY=true` 或 `SENTRY_DISABLED=true`，放宽 Sentry 校验；必须在 Step Summary 输出 `HAS_SENTRY_ORG/HAS_SENTRY_PROJECT` 与 `DOCS_ONLY` 状态，并将占位值（如 `<DOCS_ONLY_PLACEHOLDER>`）写入导出产物以示可见。
- 任何“打包/发布/上传 sourcemaps”链路严格禁止 `DOCS_ONLY/SENTRY_DISABLED`；由 `scripts/ci/guard-release-env.mjs` 前置守卫，发现即 Fail Fast。
- 所有宽松/守卫过程的结果写入 `logs/YYYYMMDD/ci/*.log`，便于审计与回溯。

## Consequences

- 正向：统一指标口径、门禁强约束、日志可追踪、故障快速回滚；文档构建在缺 Sentry 变量时保持稳定。
- 代价：引入第三方依赖与成本；合规与数据治理需要持续维护；文档链路与发布链路的策略分离要求工作流清晰配置。

## Verification

- 单元测试：`tests/unit/observability/sentry.spec.ts` 覆盖配置要点与清洗逻辑（最小）。
- 门禁脚本：`scripts/release-health-gate.mjs`、`scripts/ci/guard-release-env.mjs`。
- 监控指标：Crash‑Free Users/Sessions、错误率、版本采纳率；门禁失败按阈值 Fail Fast。

## References

- CH 章节：CH01、CH03、CH07
- 相关 ADR：ADR‑0005（质量门禁）、ADR‑0002（安全）
- 外部：Sentry Electron, Release Health 文档
- Godot 变体实现与规划：`docs/migration/Phase-16-Observability-Sentry-Integration.md`、`docs/migration/Phase-16-Observability-Backlog.md`
---

## Addendum (2025-11-08): Godot Alignment

- SDK: Replace Electron integration with Sentry Godot SDK. Initialize in an Autoload singleton during project startup; scrub PII at source（当前模板尚未集成，具体任务参见 Phase-16 Backlog B1/B2）。
- Sessions/Release Health: Map Godot sessions to releases; keep Crash-Free Users/Sessions as primary gates. Keep logs under `logs/YYYYMMDD/observability/`（当前模板仍以本地 JSONL 日志与测试报告为主，不提供 Release Health 硬门禁）。
- Test/CI: Collect GdUnit4 JUnit/XML and HTML reports under `reports/`; aggregate into CI summary. Windows-only runners (`pwsh`) remain.
- Config: Provide `sentry.dsn` and environment via `project.godot` or environment variables; disallow hard-coded secrets。
- Verification: Add a headless scene smoke that initializes Sentry and emits a controlled test error; assert it is captured in dry-run mode（Godot 侧验证路径由 Phase‑16 文档与 Backlog 进一步细化）。
