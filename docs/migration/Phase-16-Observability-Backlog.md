# Phase 16 Backlog — 可观测性与 Sentry 集成增强

> 状态：Backlog（非当前模板 DoD，按需渐进启用）
> 目的：承接 Phase-16-Observability-Sentry-Integration.md 与 ADR-0003 中尚未在当前 Godot+C# 模板落地的可观测性/Sentry 集成蓝图，避免“文档超前、实现滞后”，同时为后续项目提供可观测性优化路线图。
> 相关 ADR：ADR‑0003（可观测性与 Release Health）、ADR‑0005（质量门禁）、ADR‑0015（性能预算）

---

## B1：Observability Autoload 与 Sentry SDK 集成

- 现状：
  - 当前模板通过 `LoggerAdapter` + SecurityAudit/SqliteDataStore/SecurityHttpClient 提供最小日志与安全审计能力；
  - Phase‑16 文档与 ADR‑0003 Addendum 中提到的 `Observability.cs` Autoload 与 Sentry Godot SDK 初始化尚未落地；
  - 项目中不存在 Sentry SDK 依赖、DSN 配置或 Release/Environment 等元数据绑定。
- 蓝图目标：
  - 在 Godot 层引入 `Observability.cs` Autoload，负责：
    - 读取配置（如 `sentry_config.json` 或环境变量）并初始化 Sentry Godot SDK；
    - 设置 Release、Environment、SampleRate 等参数；
    - 提供统一的结构化日志接口（debug/info/warning/error）和异常捕获入口；
    - 尽早在启动阶段完成初始化，确保 Release Health Sessions 能覆盖主场景。
- 建议实现方式：
  - 在 Game.Godot 项目中添加 Sentry Godot SDK（兼顾 Windows-only 平台与隐私合规要求）；
  - 实现最小版 `Observability.cs`，仅负责 SDK 初始化与简单日志代理，逐步扩展其他功能；
  - 将 Sentry DSN/Release/Environment 从硬编码迁移到配置文件或环境变量，避免泄露敏感信息。
- 优先级：P2（需要真实项目环境和 Sentry 账号支持，模板阶段可暂不集成）。

---

## B2：Game.Core 观测客户端与结构化日志

- 现状：
  - `Game.Core/Ports/ILogger.cs` + `LoggerAdapter` 提供了基本的日志接口，但未与 Sentry 或统一的 ObservabilityClient 集成；
  - Phase‑16 文档中的 `Game.Core/Observability/ObservabilityClient.cs`、`StructuredLogger.cs`、`PiiDataScrubber.cs` 等仍停留在蓝图阶段。
- 蓝图目标：
  - 在 Game.Core 层实现可复用的 Observability 客户端：
    - 封装 Sentry SDK 或其他后端的初始化与上报；
    - 提供结构化日志接口（logger/level/tags/extra/breadcrumbs）；
    - 在 BeforeSend 钩子中统一处理 PII 脱敏与事件过滤；
    - 支持性能指标与自定义事件上报（与 Phase‑15 性能库联动）。
- 建议实现方式：
  - 参考 Phase‑16 文档示例，将 `ObservabilityClient`/`StructuredLogger`/`PiiDataScrubber` 落地到 `Game.Core/Observability/**`；
  - 通过依赖注入让核心服务使用 ILogger/ObservabilityClient，而不是直接依赖 Godot 或 Sentry；
  - 在 xUnit 测试中使用 fake/mock 实现验证日志/事件上报行为。
- 优先级：P3（适合在业务逻辑复杂、对日志/追踪要求较高时启用，模板阶段不强制）。

---

## B3：Release Health 门禁脚本与配置

- 现状：
  - ADR‑0003 定义了 Release Health 门禁（Crash‑Free Sessions/Users ≥99.5% 等），但当前模板未实现对应的脚本或配置文件；
  - 未发现 `.release-health.json` 或 `scripts/release_health_gate.py`/`release-health-gate.mjs` 等实现；
  - CI 工作流中也尚未出现专门的 release-health Job。
- 蓝图目标：
  - 提供一套可在 Windows CI 中运行的 Release Health Gate 脚本：
    - 从 Sentry API 读取某个 Release + Environment 的 Crash‑Free Sessions/Users 等指标；
    - 根据 `.release-health.json` 中的阈值判断是否通过；
    - 输出人类可读摘要与机器可读 JSON 报告（写入 logs/ci/**/release-health.json）。
- 建议实现方式：
  - 使用 Python 实现 `scripts/python/release_health_gate.py`，替代旧的 Node 脚本示例；
  - 在 `.release-health.json` 中定义阈值和采样窗口（24h、48h 等）；
  - 在 Windows CI/Quality Gate 工作流中增加可选的 release-health 步骤，受环境变量（SENTRY_*）控制。
- 优先级：P2–P3（需要 Sentry 账号与网络访问，适合在接入实际监控后启用）。

---

## B4：隐私与合规文档（privacy-compliance.md）

- 现状：
  - Phase‑16 文档提到 `docs/privacy-compliance.md` 作为隐私与合规文档，但当前仓库中尚未创建；
  - AGENTS/CLAUDE 中对 PII 脱敏、日志路径和隐私约束已有描述，但缺少集中、对外可读的文档模板。
- 蓝图目标：
  - 在 docs 下新增 `privacy-compliance.md`，明确：
    - 日志/审计中允许出现的字段与禁止记录的 PII 类型；
    - Sentry 事件中 PII 脱敏策略（客户端/服务端）；
    - 数据保留与删除策略（Retention）；
    - 与 ADR‑0003/ADR‑0002 的关系与引用。
- 建议实现方式：
  - 参考现有 AGENTS/CLAUDE 中的隐私相关段落，抽取成模板化文档；
  - 将该文档作为后续项目填写实际策略的起点，而不是硬编码为本模板的强约束。
- 优先级：P2（对项目合规与沟通价值高，但不阻塞模板运行）。

---

## B5：可观测性与日志使用规范（logging-guidelines.md）

- 现状：
  - AGENTS 和 testing-framework 文档中零散描述了日志路径、审计 JSONL 格式与测试输出规范；
  - Phase‑16 蓝图中提到 `docs/logging-guidelines.md`，当前仓库中尚未创建。
- 蓝图目标：
  - 提供一份统一的日志使用规范：
    - 建议 logger 命名空间（如 `game.core`, `ui.menu`, `db.access`, `security` 等）；
    - 建议 level 使用方式（debug/info/warning/error）与何时记录 Breadcrumb；
    - 与 logs/ci/**、logs/e2e/**、user://logs/** 目录结构对齐；
    - 对接 ADR‑0003 和 Phase‑16 的结构化日志维度定义（logger/level/tags/extra/breadcrumbs）。
- 建议实现方式：
  - 在 docs 下新增 `logging-guidelines.md`，基于现有规范整理；
  - 在 AGENTS 中引用该文档，而不是重复定义细节。
- 优先级：P3（主要提升可读性与团队共识，非运行时必需）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 在需要正式上线监控和发布健康门禁时，可以按 B1→B3 的顺序逐步启用 Sentry SDK、Observability Autoload 与 Release Health Gate；
  - 若对日志和隐私有更高要求，再按 B2/B4/B5 的顺序扩展 Game.Core 观测客户端、隐私文档与日志规范。

- 对于模板本身：
  - 当前 Phase 16 仅要求现有 LoggerAdapter + 安全审计（SecurityAudit/SqliteDataStore/SecurityHttpClient）提供最小可观测性基线；
  - 本 Backlog 文件用于记录 Sentry 集成与 Observability 蓝图，避免在模板阶段就强行引入第三方依赖和复杂工作流。

