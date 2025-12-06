---
PRD-ID: PRD-Guild-Manager
Title: CloudEvents Core 契约更新
ADR-Refs:
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-cloudevents-core.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/cloudevents-core.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“CloudEvents Core”契约的变更登记与验收要点（仅引用 01/02/03 章口径，不复制阈值/策略）。

变更意图（引用）

- 事件封装字段统一与命名规范：见 ADR‑0004（事件与契约统一口径）。
- 质量门禁与一致性校验：见 ADR‑0005（质量门禁）。

影响范围

- 合同文件：`src/shared/contracts/cloudevents-core.ts`
- 受影响模块：事件发布/订阅、日志与可观测性链路

验收要点

- 单测与 E2E 占位存在（见 Test‑Refs），并覆盖基本字段校验。
