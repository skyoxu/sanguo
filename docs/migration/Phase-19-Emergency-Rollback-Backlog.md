# Phase 19 Backlog — 应急回滚与监控增强

> 状态：Backlog（非当前模板 DoD，按需渐进启用）
> 目的：承接 Phase-19-Emergency-Rollback-and-Monitoring.md 中尚未在当前 Godot+C# 模板落地的自动回滚与监控蓝图，避免“文档超前、实现滞后”，同时为后续项目提供发布故障应对路线图。
> 相关 ADR：ADR‑0003（Release Health）、ADR‑0005（质量门禁）、Phase‑16（可观测性）、Phase‑17（构建与导出）、Phase‑18（分阶段发布）

---

## B1：Sentry Release Health 轮询脚本

- 现状：
  - ADR‑0003 定义了 Crash‑Free Sessions/Users 作为 Release Health 门禁标准，但当前模板尚未接入 Sentry SDK 或 Release Health API；
  - Phase‑19 文档中的“每 5 分钟检查 Crash‑Free Sessions 与 Error Rate”的监控任务尚未实现。
- 蓝图目标：
  - 提供一个可在 Windows CI/调度任务中运行的 Release Health 轮询脚本：
    - 调用 Sentry API 获取指定项目/Release/Environment 的 Crash‑Free Sessions/Users、Error Rate 等指标；
    - 根据配置阈值（例如 `.release-health.json`）判断当前 Release 状态；
    - 以 JSON 形式将监控结果写入 `logs/ci/<date>/release-health.json`，并在控制台输出摘要。
- 建议实现方式：
  - 在 Phase‑16 的基础上使用 Python 实现 `scripts/python/release_health_gate.py`，同时承担“轮询 + 门禁”两种角色；
  - 为不同渠道（Canary/Beta/Stable）在配置中定义不同阈值与观察窗口；
  - 在 Phase‑19 文档中补充调用示例和字段约定。
- 优先级：P2–P3（需要 Sentry 账号与网络访问，适合在项目有正式监控后启用）。

---

## B2：GitHub Actions 回滚工作流

- 现状：
  - 当前仓库仅提供 Windows Release 工作流（手动导出 + 上传 EXE Artifact），没有自动回滚或监控驱动的工作流；
  - Phase‑19 文档中的“自动触发回滚流程”与“标记版本 revoked”只停留在架构图层面。
- 蓝图目标：
  - 提供一条可选的“回滚工作流”（例如 `.github/workflows/windows-rollback.yml`）：
    - 触发方式：手动 dispatch、Release Health Gate 失败后的后续 Job，或外部告警系统；
    - 步骤：读取 Release Profile/版本元数据 → 选择目标 Rollback 版本 → 调用现有 Release 工作流或直接导出 → 标记 Problem 版本为 revoked（Sentry/GitHub 端）。
- 建议实现方式：
  - 在 Release 工作流的基础上，新增一个轻量的 rollback workflow，仅负责：
    - 选定要回滚到的 Release（如最近一个标记为 "stable" 的 tag）；
    - 重新触发构建或从历史 Artifact 中复制 EXE；
    - 调用 Sentry API 将 Problem 版本标记为 revoked（依赖 B1 中的 Release Health 脚本提供版本信息）。
- 优先级：P3（适合正式生产环境，模板阶段可保持人工回滚流程）。

---

## B3：客户端 ReleaseManager 与回滚提示

- 现状：
  - Godot 客户端目前没有集中管理“当前版本状态”的组件；
  - Phase‑19 文档中提到的 ReleaseManager.cs（在启动时检查版本撤销状态并提示用户更新）尚未实现。
- 蓝图目标：
  - 在 Game.Godot 或 Game.Core 中提供一个 ReleaseManager 组件：
    - 负责读取本地版本信息（如 build-info.json/release-profile.json）；
    - 可选：从远程配置/Release Health 服务获取“当前版本状态”（active/revoked）；
    - 在检测到当前版本已被 revoked 时，提示用户更新或自动跳转到更新页面（根据项目需求决定）。
- 建议实现方式：
  - 在 Phase‑17/18 的版本元数据基础上，新增简单的 ReleaseManager 类，先只负责在调试/测试场景中展示版本信息；
  - 在后续项目中，根据 Sentry/配置服务对接情况，逐步扩展为真正的回滚提示/禁用逻辑。
- 优先级：P3（偏用户体验与安全兜底，不影响模板运行）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 初期可以依赖现有的 Windows CI/Quality Gate/Release 工作流与手工回滚流程，快速完成内部发布与基本监控；
  - 当项目进入正式运营阶段、对稳定性要求较高时，可按 B1→B2→B3 的顺序逐步引入 Release Health 轮询、自动回滚 Job 与客户端 ReleaseManager。

- 对于模板本身：
  - 当前 Phase 19 不要求引入 Sentry SDK 或自动回滚脚本，只需保证文档中描述的蓝图不会与实际实现相冲突；
  - 本 Backlog 文件用于记录未来可选的“自动回滚与监控”增强，避免在模板阶段就强行引入复杂的回滚决策逻辑。

