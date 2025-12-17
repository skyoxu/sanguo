# Base-Clean 概览与索引（人工导航页）

本目录是 **Base-Clean**：用于承载跨切面与系统骨干（arc42 §01–07、09–12），不包含任何具体 PRD 内容；08 章只保留模板与写作约束。

## 使用方式

- 先读 `docs/architecture/base/01-introduction-and-goals-v2.md` 了解约束与目标，再按需读安全/可观测/门禁/性能等章节。
- Base 文档只使用占位符（如 `${DOMAIN_*}` `${PRODUCT_*}`），禁止出现 `PRD_xxx` 标识。
- 任何“落地性口径”（安全、门禁、性能、契约存放位置等）应引用对应 **Accepted ADR**，避免在 Base 多处复制阈值/策略。

## 章节导航（Base 12 章）

- 01：`docs/architecture/base/01-introduction-and-goals-v2.md`
- 02：`docs/architecture/base/02-security-baseline-godot-v2.md`
- 03：`docs/architecture/base/03-observability-sentry-logging-v2.md`
- 04：`docs/architecture/base/04-system-context-c4-event-flows-v2.md`
- 05：`docs/architecture/base/05-data-models-and-storage-ports-v2.md`
- 06：`docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md`
- 07：`docs/architecture/base/07-dev-build-and-gates-v2.md`
- 08：`docs/architecture/base/08-crosscutting-and-feature-slices.base.md`
- 09：`docs/architecture/base/09-performance-and-capacity-v2.md`
- 10：`docs/architecture/base/10-i18n-ops-release-v2.md`
- 11：`docs/architecture/base/11-risks-and-technical-debt-v2.md`
- 12：`docs/architecture/base/12-glossary-v2.md`

## 与 ADR 的对齐（当前口径）

建议从这些 ADR 开始串起全局口径：

- 运行时与发布：`docs/adr/ADR-0018-godot-runtime-and-distribution.md`
- 安全基线：`docs/adr/ADR-0019-godot-security-baseline.md`
- 性能预算与门禁：`docs/adr/ADR-0015-performance-budgets-and-gates.md`
- 可观测与发布健康：`docs/adr/ADR-0003-observability-release-health.md`
- 事件与契约：`docs/adr/ADR-0004-event-bus-and-contracts.md`、`docs/adr/ADR-0020-contract-location-standardization.md`

## 本地校验（Windows）

- Base 清洁度（禁止 Base 出现 PRD_ID/具体 08 内容）：`pwsh -File scripts/ci/verify_base_clean.ps1`
- 文本编码与疑似乱码（写入 `logs/ci/<YYYY-MM-DD>/encoding/**`）：`py -3 scripts/python/check_encoding.py --root docs/architecture/base`
- 旧技术栈术语收敛取证（可选）：`py -3 scripts/python/scan_doc_stack_terms.py --root docs/architecture/base`
