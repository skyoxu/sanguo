# 项目能力状态总览（Godot+C# 模板版）

> 目的：基于 `PROJECT_DOCUMENTATION_INDEX.md` 与 `docs/migration/Phase-*.md`，梳理当前 **Godot 4.5 + C# 游戏模板** 已具备的能力、已进入 Backlog 的能力，以及仍未实现/未迁移的能力。

本文件只关注 **与 Godot+C# 模板直接相关** 的能力；Electron/React 专用能力会统一归入“未实现/未迁移（vitegame 专用）”。

## 0. 状态标记约定

- **Implemented**：模板中已经有对应 **代码/脚本/工作流**，并在 Phase 文档或 ADR 中有 Godot 变体说明。
- **Backlog**：能力已经在某个 Phase Backlog 文档中明确描述，但当前模板未实现（供后续项目按需落地）。
- **NotImplemented / NotMigrated**：只在旧的 vitegame/Electron 文档中出现，当前 Godot 模板既未实现，也未被纳入 Backlog（通常是 Electron/React 专用能力）。

下面按大主题（基本对应 `PROJECT_DOCUMENTATION_INDEX.md` 的章节）进行归类。

---

## 1. ADR 与架构基座

对应 INDEX：章节 1（ADR）、2（Base-Clean 架构文档），以及 `docs/adr/**`、`docs/architecture/base/**`。

- 能力：技术栈与平台策略（ADR-0001/0011）  
  状态：**Implemented**  
  说明：已在 ADR 中明确 Windows-only + Godot+C# 技术栈；`ADR-0001-tech-stack.md` 仍保留部分 Electron/React 描述，但在 `ADR-0011-windows-only-platform-and-ci.md` 与 Phase-17 文档中已经收敛为 Windows + Godot 架构。

- 能力：数据存储口径（ADR-0006 + ADR-0023 + CH05/CH06 + Phase-6）  
  状态：**Implemented**  
  说明：
  - Settings SSoT = `ConfigFile`（`user://settings.cfg`），见 `ADR-0023-settings-ssot-configfile.md` 与 `Phase-6-Data-Storage.md`；
  - 领域数据使用 SQLite，通过 `SqliteDataStore` 封装，仅允许 `user://` 路径并校验路径穿越；
  - `docs/architecture/base/05-data-models-and-storage-ports-v2.md` 与 `06-runtime-view-...` 已加入 Godot+C# 变体说明。

- 能力：事件总线与契约（ADR-0004 + Phase-9）  
  状态：**Implemented（核心） + Backlog（命名收敛）**  
  说明：
  - 已实现 C# `DomainEvent` + `EventBus` + `EventBusAdapter`，事件通过 `DomainEventEmitted` Signal 暴露给 GDScript；
  - Phase-9 文档给出了 Godot 事件命名口径（`ui.menu.*`、`screen.*.*`、`core.*.*`），并说明旧的 `game.started/score.changed` 事件作为兼容示例保留；
  - 统一迁移到 `core.*.*` 命名的工作记入 `Phase-9-Signal-Backlog.md`，尚未完全落地。

- 能力：可观测性与发布健康（ADR-0003 + CH03 + Phase-16）  
  状态：**Backlog**  
  说明：
  - 文档层面已说明需要 Sentry Release Health + Crash-free Sessions ≥ 99.5% 门禁；
  - 当前 Godot 模板尚未集成 Sentry SDK，也未实现 `release-health` Python 脚本和对应 CI 工作流；
  - 相关工作集中在 `Phase-16-Observability-Backlog.md`。

- 能力：质量门禁总体口径（ADR-0005 + CH07 + Phase-13）  
  状态：**Implemented（基础门禁） + Backlog（高级门禁）**  
  说明：
  - 已实现：dotnet test + 覆盖率汇总、Godot 自检（CompositionRoot self-check）、编码扫描、GdUnit4 分集/全集运行，以及统一入口脚本 `quality_gates.py`；
  - Backlog：重复率/复杂度扫描、循环依赖检查、Sentry/Release Health 门禁、Perf P95 硬门等，详见 `Phase-13-Quality-Gates-Backlog.md` 与 Phase-15/16 Backlog 文档。

- 能力：Electron 安全基线（ADR-0002 + CH02 原版口径）  
  状态：**NotImplemented / NotMigrated（vitegame 专用）**  
  说明：
  - 原文针对 Electron（CSP、contextIsolation 等），当前 Godot 模板安全基线已重写为 Godot 文件系统/网络/插件安全（见 Phase-14 文档与 Backlog）；
  - Electron 相关条目保留为历史参考，但不适用于本模板。

---

## 2. 运行时骨干：Domain / Adapters / Data / Scenes / Signals

对应 INDEX：章节 2（Base-Clean）、6（Implementation 与 Plans），以及 Phase-3 ~ Phase-9 系列文档。

- 能力：三层架构（Game.Core / Adapters / Scenes）  
  状态：**Implemented**  
  说明：
  - `Game.Core`：纯 C# 域模型与服务，无 Godot 依赖，可通过 xUnit 快速测试；
  - `Game.Godot`：适配层（如 `SqliteDataStore`、`EventBusAdapter`、Security adapters），只在这一层与 Godot API 交互；
  - 场景层：`Main.tscn` + 屏幕系统（`ScreenNavigator` + Start/Settings Screen），以及 HUD/SettingsPanel glue 逻辑，符合 Phase-8 的 Godot 变体设计。

- 能力：数据存储与迁移（Phase-6）  
  状态：**Implemented（模板所需能力） + Backlog（高级迁移/备份）**  
  说明：
  - 已有：`SqliteDataStore` + `DbTestHelper` + 多个 Repository bridge，实现 user:// 路径校验、journal 模式配置、跨重启持久化、事务与回滚测试；
  - `Phase-6-Data-Storage.md` 与 Backlog 文档记录了更多高级迁移/备份策略（如 schema 版本管理、自动迁移钩子），仅部分实现（例如 schema_version 元表与 EnsureMinVersion）。

- 能力：场景/屏幕/Glue 层（Phase-8）  
  状态：**Implemented**  
  说明：
  - 层次：`ScreenRoot`（可切换 Screens）、`HUD`、`Overlays`、SettingsPanel/InputMapper/SettingsLoader/ThemeApplier 等 Autoload/Glue；
  - `ScreenNavigator` 支持淡入淡出过渡与 Enter/Exit 钩子；
  - GdUnit4 集成测试覆盖基本的导航流、HUD 更新、SettingsPanel show/close 及 ConfigFile 优先级。

- 能力：Signal System（Phase-9）  
  状态：**Implemented（核心链路） + Backlog（性能/命名收敛/CI 检查）**  
  说明：
  - 已有：`DomainEvent` + `EventBus` + `EventBusAdapter`（`DomainEventEmitted` Signal）、Main.gd 中的订阅与路由；
  - xUnit：`GameEngineCoreEventTests` 验证 `game.started`/`score.changed`/`player.health.changed` 事件发布；
  - Backlog：
    - 统一迁移到 `core.*.*` 命名；
    - Signal XML 注释、性能基准测试、CI 信号合规检查，均记录于 `Phase-9-Signal-Backlog.md`。

---

## 3. 测试矩阵与质量门禁（Phase 10–15）

对应 INDEX：章节 5（质量门禁）、4（工作流清单）、10（质量保障），以及 Phase-10/11/12/13/14/15 相关文档与 Backlog。

- 能力：xUnit 单元测试（Game.Core.Tests）  
  状态：**Implemented**  
  说明：
  - 已有：Domain/Engine/Services/State/Utilities 等多组测试，如 `DamageTests`、`GameEngineCoreEventTests`、`GameConfigTests`；
  - 使用 FluentAssertions + NSubstitute，支持 coverlet 覆盖率采集；
  - dotnet 测试通过 `scripts/python/run_dotnet.py` 与 `ci_pipeline.py all` 集成进 CI。

- 能力：GdUnit4 场景与适配层测试（Tests.Godot）  
  状态：**Implemented（关键小集） + Backlog（更全面覆盖）**  
  说明：
  - 已实现：Adapters（含 DB/Config/FeatureFlags）、Security、Integration、UI、Scenes 小集，均可 headless 运行；
  - Adapters+Security 作为硬门禁小集；Integration/Db/UI 作为软门禁；
  - Backlog：更多 A11y/UI/复杂交互的用例，以及更高覆盖率目标，记录在 Phase-11/14/20 Backlog 文档中。

- 能力：Headless Smoke 与 Perf P95 门禁（Phase-12/15）  
  状态：**Implemented（基础能力） + Backlog（更严格门禁）**  
  说明：
  - 已有：`smoke_headless.ps1` + `smoke_exe.ps1`、PerfTracker Autoload + `check_perf_budget.ps1`，可在本地或 CI 运行；
  - `Phase-12-Headless-Smoke-Backlog.md`、`Phase-15-Performance-Budgets-Backlog.md` 中记录了更严格的判定规则（如必须看到 `[TEMPLATE_SMOKE_READY]`、渠道特定 Perf gate），尚未全部落地为硬门禁。

- 能力：统一质量门禁脚本（Phase-13，quality_gates.py）  
  状态：**Implemented（入口统一） + Backlog（10 项门禁全量脚本化）**  
  说明：
  - 已有：`quality_gates.py all` 作为 Python 入口，内部调用 `ci_pipeline.py all`；
  - CI 中通过 `scripts/ci/quality_gate.ps1` 调用；
  - 尚未完全按照蓝图实现所有 10 项门禁（重复率、复杂度、循环依赖、Sentry 等），对应条目在 Phase-13/15/16 Backlog 中。

---

## 4. 安全基线与审计（Phase 14）

对应 INDEX：章节 2/5/7 中的安全部分，以及 Phase-14 文档与 Backlog。

- 能力：HTTP 安全客户端（SecurityHttpClient）  
  状态：**Implemented**  
  说明：
  - 支持仅 HTTPS、主机白名单、方法限制、Body 大小限制，阻断时写审计日志并发出 Signal；
  - 有 GdUnit4 测试覆盖 allow/deny/invalid 场景；
  - 详细口径见 `Phase-14-Godot-Security-Baseline.md`。

- 能力：SQLite 路径与权限守卫（SqliteDataStore）  
  状态：**Implemented**  
  说明：
  - 仅允许 user:// 前缀、禁止路径穿越与绝对路径；
  - 失败写入 `logs/ci/<date>/security-audit.jsonl`，并在 GdUnit4 中有测试；
  - 更通用的文件系统守卫与多模块审计聚合留在 Backlog。

- 能力：安全测试矩阵  
  状态：**Implemented（5 个测试文件） + Backlog（扩充到 8+）**  
  说明：
  - 已覆盖：HTTP 安全、DB 安全、Config 安全等核心用例；
  - `Phase-14-Godot-Security-Backlog.md` 中记录了 URL 白名单单元测试、文件系统保护测试、信号契约测试等扩展目标。

- 能力：Electron 安全（CSP 等）  
  状态：**NotImplemented / NotMigrated（vitegame 专用）**  
  说明：仅保留在 ADR/旧 Phase 文档中作为历史资料，对当前 Godot 模板不适用。

---

## 5. 构建 / 导出 / 发布 / 回滚（Phase 17–19）

对应 INDEX：章节 4（工作流）、7（渐进发布与回滚）、8（问题排查），以及 Phase-17/18/19 文档与 Backlog。

- 能力：Windows 导出与冒烟（Godot Export + Smoke）  
  状态：**Implemented**  
  说明：
  - `export_windows.ps1` 通过 Godot headless 导出 exe/pck，并支持 `.export_exclude`、preset 自动解析、日志归档；
  - `smoke_exe.ps1` + `smoke_headless.ps1` 实现基础冒烟；
  - Phase-17 系列文档（含 Quickstart/Checklist/Addendum）已对齐 Windows-only Godot 变体。

- 能力：统一质量 Gate + Export 流程  
  状态：**Implemented（基础）**  
  说明：
  - CI 工作流 `ci-windows.yml` 与 `windows-quality-gate.yml` 已接入 Python 门禁脚本、GdUnit4、小范围导出/Smoke；
  - 完整的“仅在所有门禁绿灯后执行导出并上传制品”的自动发布 pipeline 仍为项目级工作，记入 Phase-17 Backlog。

- 能力：渐进发布 / Canary / 渠道策略（Phase-18）  
  状态：**Backlog**  
  说明：
  - 文档层面已有分渠道发布、Release Profile、Sentry Release Health 驱动发布等策略说明；
  - 具体实现（不同渠道配置、自动化 pipeline、灰度门禁）尚未在 Godot 模板中落地，集中记录在 `Phase-18-Staged-Release-Backlog.md`。

- 能力：应急回滚与监控（Phase-19）  
  状态：**Backlog**  
  说明：
  - 文档中有“回滚脚本、环境切换、监控触发回滚”等蓝图；
  - 当前模板只具备基础导出与 Smoke 能力，未实现完整的自动回滚与监控联动，集中记录在 `Phase-19-Emergency-Rollback-Backlog.md`。

---

## 6. Feature Flags / PerfTracker / 观测与调试（Phase 18/21 等）

- 能力：FeatureFlags Autoload（基础开关管理）  
  状态：**Implemented（基础能力） + Backlog（高级策略）**  
  说明：
  - 已实现 Autoload `FeatureFlags`，支持 ConfigFile + 环境变量覆盖（GAME_FEATURES 等），并有 GdUnit 测试覆盖基础开关逻辑；
  - 更复杂的渠道级 Canary/实验分流、与 Release Profile/Sentry 联动的策略均记入 Phase-18 Backlog。

- 能力：PerformanceTracker Autoload 与 P95 检查  
  状态：**Implemented**  
  说明：
  - Autoload 采集帧耗时，记录 `p95_ms` 等指标，并输出到用户目录与日志；
  - `check_perf_budget.ps1` 可以在 CI 或本地解析日志并与预算比较；
  - 更复杂的基线管理、场景级 Perf 预算与多环境比较在 `Phase-15-Performance-Budgets-Backlog.md` 与 `Phase-21-Performance-Optimization-Backlog.md` 中描述。

- 能力：可观测性（Sentry / Release Health / 日志聚合）  
  状态：**Backlog**  
  说明：
  - 当前仅有本地日志与简单 Perf/Audit JSONL 输出；
  - Sentry SDK 集成、Release Health 拉取与质量看板等能力尚未落地，集中在 Phase-16/18 Backlog 与 ADR-0003 补充说明中。

---

## 7. 文档、Release Notes 与 AI 协作（Phase 20–22）

对应 INDEX：章节 0、7、8、9、10，以及 Phase-20/21/22 文档与 Backlog。

- 能力：文档导航与索引（本文件 + PROJECT_DOCUMENTATION_INDEX）  
  状态：**Implemented**  
  说明：
  - `PROJECT_DOCUMENTATION_INDEX.md` 提供完整文档索引；
  - 本文件补充了“能力状态视角”的索引，帮助区分模板已具备能力与 Backlog/未迁移能力。

- 能力：功能验收与测试说明（Phase-20）  
  状态：**Implemented（核心说明） + Backlog（项目级完整验收）**  
  说明：
  - Phase-20 文档描述了如何将 GdUnit4/xUnit/Smoke/Perf 等组合成验收流程；
  - `Phase-20-Functional-Acceptance-Backlog.md` 中保留了更完整的项目级验收脚本与报告格式，当前模板未全部实现。

- 能力：Release Notes 模板与脚本（Phase-22）  
  状态：**Implemented（模板 + 基础脚本） + Backlog（自动数据填充）**  
  说明：
  - 已有 Release Notes 模板与基础生成脚本，可以从当前版本信息生成骨架；
  - 自动从 `quality-gate-summary.json` / export 结果等 JSON 汇总填充“质量结果”段落的能力尚未实现，记录在 `Phase-22-Documentation-Backlog.md`。

- 能力：AI 协作规则（CLAUDE.md / AGENTS.md / mcp 配置）  
  状态：**Implemented**  
  说明：
  - 已有 CLAUDE/AGENTS 规范与 Codex MCP 配置；
  - 支持在本模板中使用多种 AI 助手进行协作开发，符合 INDEX 中“AI 优先开发框架”“多 AI 助手协作”的设计目标。

---

## 8. 汇总视角

从 `PROJECT_DOCUMENTATION_INDEX.md` + `docs/migration/Phase-*.md` 的角度看当前 **Godot+C# 游戏模板**：

- 已实现（Implemented）：
  - 三层架构（Domain/Adapters/Scenes）、ConfigFile+SQLite 数据存储、EventBus + Signal System 基线；
  - xUnit + GdUnit4 测试矩阵、基础质量门禁（dotnet 自测、自检、编码扫描、关键 GdUnit 小集）；
  - Windows 导出与 Smoke、PerfTracker 与基本 P95 检查、安全基线（HTTP/DB/Config）与审计输出；
  - 文档索引、Release Notes 模板、AI 协作规范。

- 已入 Backlog（Backlog）：
  - 更严格和更全面的质量门禁（重复率/复杂度/循环依赖/Sentry Release Health 等）；
  - 更丰富的安全测试集（Signal 契约、文件系统守卫等）；
  - 渠道级 Canary/Release Profile/Sentry 驱动发布与自动回滚；
  - 高阶 Perf 预算管理（基线、对比、多场景预算）；
  - 文档与 Release Notes 与 JSON 质量结果的全自动对接。

- 未实现/未迁移（NotImplemented / NotMigrated，主要为 vitegame/Electron 专用能力）：
  - Electron 主进程/渲染进程安全策略与前端打包流程；
  - React/Phaser 前端组件与相关测试/构建工作流；
  - 仅在旧文档中出现、与 Godot 模板无直接映射的工具或脚本。

后续若继续演进本模板，建议：

1. 优先从各 Phase 的 Backlog 文档中选择与“游戏模板可复制性”强相关的项（如 Sentry / Release Health、Perf 基线、更多 GdUnit 场景用例）逐步落地。
2. 对 Electron/vitegame 专用能力，若未来不计划迁移到 Godot，可在相应 Phase 文档中显式标注为“历史参考，不适用于 Godot 模板”，进一步减少歧义。


