---
PRD-ID: PRD-SANGUO-T2
Title: 08-T60 每局胜利与结算界面
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH06
---

# T60：每局胜利与结算界面

本页为 T60 的功能纵切拆页。胜负由 Core 判定，UI 只展示（不自判、不自算）。

## 范围
- Core 定义并判定胜利/失败条件（止损版先 1 条规则）。
- 满足条件后进入结算界面展示 winner/原因/统计快照（来自事件或投影）。

## 非目标
- 不做胜利条件自定义编辑器。

## 口径冻结
- 玩家控制角色资金 <=0 时立刻触发失败并结束游戏；AI 出局在 `turn.advanced` 后统一检查终局。
- 出局处理必须发布 `core.sanguo.player.eliminated`（审计）并释放资产为无主；释放/买下/夺取导致的归属变化必须发布 `core.sanguo.city.owner.changed`。
- `sequence` 仅用于审计落盘/复盘稳定排序，不进入域事件 payload。

## 契约（EventType + 触发点）
- `core.sanguo.game.ended`：满足胜利/失败条件并进入结算前。
- `core.sanguo.player.eliminated`：玩家/AI 出局并进入释放资产流程时（审计）。
- `core.sanguo.city.owner.changed`：城池归属变化时（买下/释放/夺取）。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/GameEvents.cs`、`Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T60.1 满足条件时发布 `core.sanguo.game.ended` 并进入结算界面。
- ACC:T60.2 结算界面展示 winner/原因/统计快照（来自事件或投影）。

## Test-Refs
- `Tests.Godot/tests/UI/test_task60_game_end_screen.gd`
