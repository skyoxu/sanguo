---
PRD-ID: PRD-Guild-Manager
Title: 公会管理事件（Guild Manager Events）契约更新
ADR-Refs:
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-guild-manager-events.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/guild/guild-manager-events.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“公会管理事件”契约更新的记录与验收口径。

变更意图（引用，不复制口径）

- 事件命名遵循统一规范 `${DOMAIN_PREFIX}.<entity>.<action>`（ADR‑0004）；
- 质量门禁与变更追踪引用 ADR‑0005；

影响范围

- 合同文件：`src/shared/contracts/guild/guild-manager-events.ts`
- 受影响模块：公会管理场景的事件发布/订阅、前端状态同步

验收要点（就地）

- 单测覆盖事件构造与必需字段；E2E 占位用例存在（见 Test-Refs）
