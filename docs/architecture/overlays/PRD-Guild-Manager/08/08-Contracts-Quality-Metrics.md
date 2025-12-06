---
PRD-ID: PRD-Guild-Manager
Title: 质量指标（Quality Metrics）契约更新
ADR-Refs:
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-quality-metrics.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/quality/metrics.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“质量指标”契约更新的记录与验收口径。

变更意图（引用，不复制口径）

- 指标事件与 DTO 统一归口（ADR‑0004），相关阈值与门禁由基线章节维护（ADR‑0005），此处仅登记功能影响与测试。

影响范围

- 合同文件：`src/shared/contracts/quality/metrics.ts`
- 受影响模块：性能埋点、发布健康、报表聚合

验收要点（就地）

- 单测覆盖基本结构；E2E 占位用例存在（见 Test-Refs）
