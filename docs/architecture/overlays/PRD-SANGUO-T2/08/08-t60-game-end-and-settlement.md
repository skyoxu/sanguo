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

## 契约（EventType + 触发点）
- `core.sanguo.game.ended`：满足胜利/失败条件并进入结算前。

## 验收条款（ACC）
- ACC:T60.1 满足条件时发布 `core.sanguo.game.ended` 并进入结算界面。
- ACC:T60.2 结算界面展示 winner/原因/统计快照（来自事件或投影）。

## Test-Refs
- `Tests.Godot/tests/UI/test_task60_game_end_screen.gd`

