---
PRD-ID: PRD-Guild-Manager
Title: 安全事件与策略契约更新（Security Contracts）
ADR-Refs:
  - ADR-0002
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-security.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/security.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“Security Contracts”变更登记与验收要点（仅引用 01/02/03 章口径，不复制阈值/策略）。

变更意图（引用）

- Electron 安全基线：见 ADR‑0002（CSP、contextIsolation 等）。
- 契约与事件统一：见 ADR‑0004。
- 质量门禁与发布健康：见 ADR‑0005。

影响范围

- 合同文件：`src/shared/contracts/security.ts`
- 受影响模块：安全事件、策略校验与日志告警链路

验收要点

- 单测与 E2E 占位存在（见 Test‑Refs）。
