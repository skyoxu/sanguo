# ADR-0026: 事件发布失败策略（PublishAsync Failure Semantics）

- Status: Accepted
- Context: Task 8 已完成，但“PublishAsync 失败如何处理”口径未显式固化；该口径会影响所有事件驱动任务与验收门禁。
- Decision:
  - `IEventBus.PublishAsync(DomainEvent)` 的实现必须具备“防御性”：**不因订阅者异常而失败**，订阅者异常必须被捕获并记录（ILogger/IErrorReporter），并继续执行其他订阅者。
  - 发布实现不得因为“辅助路径”异常而让调用方进入不可控状态：例如序列化/日志/上报失败必须被隔离，避免把异常传播给业务调用方。
  - 业务层（Core Services）允许 fire-and-forget（`_ = PublishAsync(...)`），但前提是事件总线实现满足上述“不抛异常/不返回 faulted task”的约束；否则调用方必须显式 await 并处理异常。
  - 对“会改变领域状态且必须产生事件”的操作（例如购买/过路费结算），应提供防御性回归用例：当事件总线异常时，领域状态不得进入半提交状态（可选择回滚或 fail-fast；本仓库当前采用“回滚 + 抛出带上下文异常”的防御策略，见回归用例）。
- Consequences:
  - 正向：避免“某个 handler 抛异常 → 整条事件链崩溃/产生未观察到的 Task 异常”；降低单机单人游戏的崩溃概率；便于在 CI 与本地通过确定性证据定位问题。
  - 代价：发布路径需要更严格的异常隔离与测试；会增加少量日志/上报噪声（可通过采样/过滤处理，口径见 ADR-0003/0019）。
- References:
  - ADR-0004（事件总线与契约）
  - ADR-0003（可观测性与 Release Health）
  - ADR-0018 / ADR-0025（测试策略）
  - ADR-0019（安全基线：审计与落盘）

