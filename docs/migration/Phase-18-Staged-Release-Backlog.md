# Phase 18 Backlog — 分阶段发布与 Canary 策略

> 状态：Backlog（非当前模板 DoD，按需渐进启用）
> 目的：承接 Phase-18-Staged-Release-and-Canary-Strategy.md 中尚未在当前 Godot+C# 模板落地的发布/Canary 蓝图，避免“文档超前、实现滞后”，同时为后续项目提供发布策略演进路线图。
> 相关 ADR：ADR‑0003（Release Health）、ADR‑0005（质量门禁）、Phase‑16（可观测性）、Phase‑17（构建与导出）

---

## B1：渠道级 Canary 策略（按受众分层放量）

- 现状：
  - 模板提供了 `Game.Godot/Scripts/Config/FeatureFlags.cs` 与环境变量/配置文件驱动的 FeatureFlags 机制；
  - Phase‑18 文档仅给出“demo_screens/perf_overlay 等 Flag”的最小使用示例，没有定义按渠道（QA/内测/灰度/正式）分层的标准策略；
  - CI/工作流层面也未区分不同受众群体的启用范围（所有构建视为同一环境）。
- 蓝图目标：
  - 将 Canary 策略从“单 Flag”提升到“渠道级配置”：
    - 例如定义 `channel=qa/internal/beta/stable` 的环境变量或配置文件；
    - 按渠道启用不同的 FeatureFlags 组合（QA 开最多，stable 最保守）；
    - 在 Release Notes 或版本元数据中记录当前渠道与 Flag 集合，便于回溯。
- 建议实现方式：
  - 构建期或运行时引入 `RELEASE_CHANNEL` 概念（如 `qa/internal/beta/stable`）；
  - 在 FeatureFlags 中增加按渠道的默认配置（如 `features.qa.json` 等），并允许环境变量覆盖；
  - 在 Phase‑18 主文档中补充渠道划分示例和启用建议。
- 测试增强建议：
  - 为 `FeatureFlags` 增补 GdUnit4 测试用例，覆盖：
    - `FEATURE_<NAME>` 环境变量优先级；
    - `GAME_FEATURES` 列表解析；
    - 配置文件持久化与跨重启行为；
    - 空字符串/未知 Flag 等边界情况。
- 优先级：P2（实际项目需要分层放量时启用，模板阶段不强制）。

---

## B2：Release Profile 与元数据

- 现状：
  - 当前 Release Notes 只记录版本号与基础质量门禁结果（dotnet/GdUnit/smoke/perf）；
  - 构建/导出阶段未生成独立的“Release Profile”元数据文件描述启用的 FeatureFlags/渠道/目标受众；
  - Phase‑17 的版本信息与 Phase‑18 的 Canary 策略尚未在数据层打通。
- 蓝图目标：
  - 为每次发布生成一份 Release Profile：
    - 内容包含：版本号、渠道、启用的 Flags 列表、构建时间、触发者等；
    - 以 JSON/Markdown 形式同时记录在 `docs/release/` 与 `build/` 或 `logs/ci/**` 中；
    - 方便事后将 Crash/Release Health 数据与具体 Flag 组合/渠道关联起来分析。
- 建议实现方式：
  - 在构建脚本（Phase‑17 B1）中读取 `RELEASE_CHANNEL` 与 FeatureFlags 配置，生成 `build/release-profile.json`；
  - 在 Release Notes 生成脚本中增加“Channel/Flags/Quality Gate 结果”段落：
    - 从 release-profile JSON 中拉取渠道与 Flags 信息；
    - 从 `logs/ci/<date>/ci-pipeline-summary.json`、`logs/ci/<date>/export/summary.json` 或其他汇总 JSON 中自动填充 dotnet/GdUnit/smoke/perf 等结果；
  - 在 Phase‑18 文档中给出 Release Profile 的字段示例与推荐使用方式。
- 优先级：P2–P3（主要用于后续分析和回溯，不影响最小发布可用性）。

---

## B3：Sentry Release Health 驱动的发布门禁

- 现状：
  - ADR‑0003 定义了基于 Sentry Sessions/Users 的 Release Health 门禁，但当前模板尚未集成 Sentry SDK 或 release-health gate 脚本；
  - Phase‑18 目前仅依赖 Quality Gate + smoke + 可选 perf budget 做 go/no-go 判定，没有真正的 Crash‑Free 指标驱动发布策略。
- 蓝图目标：
  - 在具备 Sentry 集成的情况下，将 Release Health 纳入发布决策：
    - 在 Canary 渠道收集一段时间的 Release Health 数据（Crash‑Free Sessions/Users、错误率等）；
    - 仅当 Canary 渠道指标满足 ADR‑0003 阈值时才允许扩大放量或合并到 stable 渠道；
    - 在 CI 中增加 release-health gate 步骤，读取最新 Release 的指标并输出决策摘要。
- 建议实现方式：
  - 等 Phase‑16 完成 Sentry SDK + release_health_gate 脚本后，在 Phase‑18 的 Release 工作流（Phase‑17 B3）中插入 release-health 检查；
  - 为 Canary 渠道和 Stable 渠道分别定义 Release Health 阈值和观察窗口；
  - 在 Release Notes 中记录该次发布的 Release Health 快照链接或摘要。
- 优先级：P3（需要真实监控环境与数据样本，适合在项目成熟期启用）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 初期可以仅使用 Quality Gate + smoke + FeatureFlags 的最小策略，不必启用渠道级分层或 Sentry 驱动门禁；
  - 当项目需要严肃的灰度发布与回滚策略时，可按 B1→B2→B3 的顺序逐步引入渠道、Release Profile 与 Release Health Gate。

- 对于模板本身：
  - 当前 Phase 18 仅要求 Quality Gate 流程完整、FeatureFlags 可用、Release Notes 脚本能生成模板；
  - 本 Backlog 文件用于记录更高级别的分阶段发布与 Canary 蓝图，避免在模板阶段就强行引入复杂的发布决策逻辑。
