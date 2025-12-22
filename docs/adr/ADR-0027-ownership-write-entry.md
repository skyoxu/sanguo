# ADR-0027: 所有权唯一写入口（Ownership Write Entry）

- Status: Accepted
- Context: Task 12 已完成购买逻辑，但“所有权由哪个 Core 组件统一判定/写入”口径需要固化，否则后续任务（事件、AI、UI）会出现多处写入导致的状态漂移与难以复现的问题。
- Decision:
  - “所有权判定”（某资源/地块当前属于谁）必须由 **单一的全局上下文组件** 裁决（需要玩家集合 + 资源集合），并对“多重所有者”视为状态损坏并抛异常。
  - “所有权写入”（购买、破产释放等会改变 OwnedIds 的操作）只允许在 **Core 领域/服务层** 内执行，并通过受控入口完成（UI/AI/Adapters 不得直接改 OwnedIds）。
  - 领域内部变更方法不作为外部调用入口，应通过可见性收敛（例如 `internal` + `InternalsVisibleTo(<CoreTests>)`）限制越界调用。
  - 本仓库的具体落地（Example, SSoT）：
    - 判定入口：`Game.Core.Domain.SanguoBoardState.TryGetOwnerOfCity(...)` / `TryBuyCity(...)`
    - 对外入口：`Game.Core.Services.SanguoEconomyManager.TryBuyCityAndPublishEventAsync(...)`
    - 领域内部变更：`Game.Core.Domain.SanguoPlayer.TryBuyCity(...)`、`TryPayTollTo(...)`（internal）
- Consequences:
  - 正向：避免 UI/AI/Adapters 直接写入导致的“绕过全局唯一性检查”；提高验收一致性；便于在 acceptance_check 中加入确定性约束。
  - 代价：测试项目需要 `InternalsVisibleTo` 才能覆盖领域内部方法；上层调用需要走服务/BoardState 入口而不是直接调用 Player 方法。
- References:
  - ADR-0021（C# Domain Layer Architecture）
  - ADR-0004（事件总线与契约：购买/支付产生事件）
  - ADR-0005（质量门禁：覆盖率与回归用例）
