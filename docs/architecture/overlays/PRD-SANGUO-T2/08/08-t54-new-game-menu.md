---
PRD-ID: PRD-SANGUO-T2
Title: 08-T54 新游戏配置界面（地图/人数/资金档/间隔/选角）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0019
Arch-Refs:
  - CH04
  - CH06
---

# T54：新游戏配置界面（唯一开局入口）

本页为 T54 的功能纵切拆页。新游戏配置界面是唯一开局入口，其输出必须固化为 `GameStartConfig`（见 T50）。

## 范围
- 选择地图（map_id）。
- 选择总人数（含玩家）：4–8。
- 选择初始资金档（5000 / 10000 / 20000）。
- 选择全局事件间隔回合数（5 / 10 / 20）。
- 玩家选择 1 个角色；剩余席位由 AI 随机补位（不可重复）。

## 非目标
- 不做设置持久化与跨次启动记忆（后续任务）。

## 验收条款（ACC）
- ACC:T54.1 UI 可完成上述配置并进入游戏。
- ACC:T54.2 AI 补位：角色全局唯一，不与玩家重复。

## Test-Refs
- `Tests.Godot/tests/UI/test_task54_new_game_menu_flow.gd`

