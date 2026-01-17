---
PRD-ID: PRD-SANGUO-T2
Title: 08-T57 行动卡（BeforeRoll，止损版）
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH06
---

# T57：行动卡（BeforeRoll，止损版）

本页为 T57 的功能纵切拆页。行动卡只在 BeforeRoll 窗口可用，止损版每回合最多 1 张（0/1）。

## 范围
- 行动卡配置只读（`res://Data/**`）。
- 使用窗口：TurnPhase.BeforeRoll。
- 效果表达：`effectKind=economyStepDelta` + `stepDelta`（steps 为整型步进，1=+0.5；最终仍按 T51 口径 clamp），并携带 `durationRounds`。

## 非目标
- 不做多卡连锁与复杂卡牌规则。

## 契约（EventType + 触发点）
- `core.sanguo.action_card.played`：行动卡被使用后发布。

## 验收条款（ACC）
- ACC:T57.1 行动卡只允许 BeforeRoll 使用，且 0/1。
- ACC:T57.2 使用行动卡后发布 `core.sanguo.action_card.played`，并影响本回合经济倍率快照。

## Test-Refs
- `Game.Core.Tests/Tasks/Task57ActionCardTests.cs`
