---
PRD-ID: PRD-Guild-Manager
Title: CloudEvent 契约更新（事件封装与字段）
ADR-Refs:
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-cloudevent.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/events/CloudEvent.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“CloudEvent”契约更新的记录与验收口径。

变更意图（引用，不复制口径）

- 统一事件封装与字段必填校验（见 ADR‑0004）；保持跨模块一致的事件命名规范 `${DOMAIN_PREFIX}.<entity>.<action>`。
- 质量门禁引用 ADR‑0005，相关测试与校验在 CI 执行。

影响范围

- 合同文件：`src/shared/contracts/events/CloudEvent.ts`
- 受影响模块：事件总线发布/订阅、日志关联与可观测性埋点

验收要点（就地）

- 单测覆盖基本构造与字段校验；E2E 占位用例存在（见 Test-Refs）
