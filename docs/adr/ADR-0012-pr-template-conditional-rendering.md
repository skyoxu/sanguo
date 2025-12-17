# ADR-0012: PR 模板（静态）与审查信息最小集

- Status: Accepted
- Date: 2025-12-16
- Related: ADR-0005（质量门禁）、ADR-0011（Windows-only）、ADR-0019（安全基线）、ADR-0020（Contracts SSoT）

## Context

模板仓库需要一个“开箱即用”的 PR 填写规范，让贡献者在不依赖额外工具链的前提下，提交时能补齐：

- 任务 ID 与回链（NG/GM）
- 关联 ADR 与 C4 组件
- Contracts 与 Overlay 08 同步检查
- 测试/门禁与 Sentry 软门禁取证

## Decision

采用 **静态 PR 模板**，并以脚本校验作为补充：

- PR 模板文件：`.github/PULL_REQUEST_TEMPLATE.md`
- Contracts 引用校验：`py -3 scripts/python/validate_contracts.py`
- 任务回链校验：`py -3 scripts/python/task_links_validate.py`

说明：

- 本仓库不启用“基于文件变更的动态模板渲染”（避免引入额外依赖与维护成本）。
- 质量门禁以 CI 工作流与 `scripts/ci/quality_gate.ps1` 为准（见 ADR-0005）。

## Consequences

- 正向：无需额外工具即可保证 PR 信息一致性；与模板可复制目标一致。
- 代价：静态模板对不同类型变更不做自动裁剪，需要贡献者自行勾选相关项。

