---
PRD-ID: PRD-Guild-Manager
Title: 预加载白名单（Preload Whitelist）契约调整
ADR-Refs:
  - ADR-0004
  - ADR-0005
Test-Refs:
  - tests/unit/contracts/contracts-preload-whitelist.spec.ts
  - tests/e2e/contracts/contracts-docs-sync.spec.ts
Contracts-Refs:
  - src/shared/contracts/electron/preload-whitelist.ts
Status: Proposed
---

本页为功能纵切（08 章）对应“预加载白名单”契约的变更说明与验收约束。

变更意图（引用，不复制口径）

- 引用 01/02/03 章的统一口径：事件与契约治理（ADR‑0004）、质量门禁（ADR‑0005）。
- 主进程与预加载暴露 API 必须遵循白名单策略；任何新增导出需在契约中显式声明并通过此页落档。

影响范围

- 合同文件：`src/shared/contracts/electron/preload-whitelist.ts`
- 受影响模块：Electron 预加载桥、渲染进程 API 访问路径

验收要点（就地）

- 存在对应的单元/端到端占位测试（见 Test-Refs）
- 变更的导出项均在契约中声明，未出现未授权导出

回归与风控

- 仅通过 contextBridge 白名单暴露 API；禁止放宽 Electron 安全基线（详见 ADR‑0002）
