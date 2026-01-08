# ADR-0030: Core 线程模型（Single-Thread Core + 明确跨线程边界）

- Status: Accepted
- Context: 本项目以 “Game.Core 纯 C# + 可单测” 为骨干，但 AI/事件/可观测容易引入后台线程与并发回调。如果不显式定义线程模型，常见后果是：Core 状态被跨线程访问导致隐性竞态、偶现回归、或“测试绿但实机炸”。需要明确哪些对象只能在单线程内变更、哪些边界允许并发、以及跨线程时的唯一合法入口。

## Decision

### 1) Core 领域对象默认线程封闭（Thread-Confined）

- 领域对象（例如玩家、棋盘状态、金库等）必须在创建它们的线程内使用与变更。
- 通过 `ThreadAccessGuard` 强制执行（运行时 fail-fast）。
- 任何需要跨线程的数据传递必须以不可变快照/DTO 形式传递（例如 SaveSnapshot、只读 View）。

### 2) 事件处理器不得修改 Core 领域状态

- 事件发布/订阅属于“通知机制”，订阅者可能并发运行；因此订阅者不得修改 Core 聚合/实体。
- 允许订阅者做：
  - 只读投影（UI 更新、日志、回放记录）
  - 触发受控入口（例如由 Glue 层在主线程调用 Core 服务推进一步）
- 禁止订阅者做：
  - 直接修改 `SanguoPlayer` / `SanguoBoardState` 等 Core 状态

### 3) AI 策略必须确定性且线程安全

- AI 策略实现必须：
  - 在同一输入下输出可回归结果（DecisionType/Reason/DecisionNode）
  - 不依赖 Godot API、不访问可变全局状态
  - 如需内部状态，必须自行加锁或改为无状态策略

### 4) 允许后台线程的范围与回到主线程的规则

- 允许在后台线程做“纯计算”（例如启发式评分、路径评估），但结果必须以不可变结果对象返回。
- 把结果应用到 Core 状态必须回到 Core 所在的单线程执行（由 Glue/调度器负责）。

## Consequences

- 正向：降低偶发竞态与 flaky；单测与实机一致性更高；更容易把稳定性条款落到可证明的门禁。
- 代价：需要明确区分“计算”与“提交”；事件订阅者需要保持只读或通过受控入口回到主线程。

## References

- ADR-0021: C# 领域层架构
- ADR-0004: 事件总线与契约
- docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md

