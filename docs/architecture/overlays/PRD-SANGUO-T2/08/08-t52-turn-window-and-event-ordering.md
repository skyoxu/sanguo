---
PRD-ID: PRD-SANGUO-T2
Title: 08-T52 回合窗口（BeforeRoll）与事件触发顺序
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH06
---

# T52：回合窗口（BeforeRoll）与事件触发顺序

本页为 T52 的功能纵切拆页。目标是把“窗口/顺序”锁死为可测口径，避免 UI 与玩法靠猜。

## 范围
- 锁死回合阶段（至少包含 TurnPhase.BeforeRoll）。
- 止损版每回合最多使用 1 张行动卡（0/1）。
- 锁死同一回合内的触发顺序：行动卡窗口 → 掷骰 → 移动 → 落点 → 事件格触发/全局事件 → 结算/回合推进（顺序以实现为准，但必须固定且可测）。

## 非目标
- 不做多卡连锁。
- 不做 PVP。

## 契约（EventType + 触发点）
- `core.sanguo.action_card.played`：BeforeRoll 使用行动卡后。
- `core.sanguo.random_event.applied`：随机事件效果应用后（含事件格与全局事件两类来源）。
  - 口径止损：`applied` 必须表示“效果已提交到 Core 的可复盘状态”，而不是“已抽取/已选择”。
  - 对 `economyStepDelta`：事件 payload 必须包含 `AppliedMultipliersAfter`（提交后快照；含 clamp 后的 EffectiveSteps 与可审计的分解来源）。

## 验收条款（ACC）
- ACC:T52.1 BeforeRoll 窗口每回合只允许 0/1 张行动卡。
- ACC:T52.2 同一回合内“事件格触发 + 每N回合全局事件”的顺序固定且可测。
- ACC:T52.3 任意顺序相关行为可从事件日志复盘（以事件序列为准）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs`
- `Game.Core.Tests/Tasks/Task52EventTriggerOrderTests.cs`
- `Game.Core.Tests/Tasks/Task52OutOfOrderEventRegressionTests.cs`

