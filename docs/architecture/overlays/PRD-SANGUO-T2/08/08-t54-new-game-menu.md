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
- 选择地图（map_id）：地图列表只来自 `res://Data/maps/_index.json`（按 name 排序，不扫描目录）。
  - 展示：`name_key`、`description_key`、`recommended_players_min/max`、`version`、`preview_image_res_path`。
  - 数据无效地图仍显示但置灰，并显示错误提示（不可选）。
- 选择总人数（含玩家）：4–8。
- 选择初始资金档（5000 / 10000 / 20000）。
- 选择全局事件间隔回合数（5 / 10 / 20）。
- 玩家选择 1 个角色；剩余席位由 AI 随机补位（不可重复）。
- 点击开始后进入 Loading（轮播/遮罩）；收到首个 `core.sanguo.game.turn.started` 才隐藏菜单；启动失败则弹窗错误并回滚到配置界面（不提供重试按钮）。

## 非目标
- 不做设置持久化与跨次启动记忆（后续任务）。

## 口径冻结
- UI 永远保持“一个有效选择”（默认选中第一张可用地图 + 第一个角色）；未选地图/未选角色时禁用开始按钮（但默认会自动选中）。
- `players_count` 表示“包含玩家在内的总人数”；范围外值必须拦截，禁止开始。
- 启动超时默认 20 秒（可由环境变量覆盖）；超时/失败必须清理已创建的 GameLoop/状态，并回滚到配置界面（回滚到默认地图/默认角色/默认人数并重生 seed）。
- 错误提示只允许 `error_code + message_key + params`（T50 口径）；message_key 缺失允许降级显示 key，但必须审计。

## 契约（EventType + 触发点）
- `core.sanguo.game.started`：点击开始后，GameStartConfig 校验通过并进入主循环时。
- `core.sanguo.game.turn.started`：启动完成后，首个回合开始（用于 UI 确认“已进入可玩态”）。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/GameEvents.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T54.1 Given 有效地图与角色可选 When 点击开始 Then 进入 Loading 且在收到首个 `core.sanguo.game.turn.started` 前不隐藏菜单。
- ACC:T54.2 Given 选择总人数与玩家角色 When 点击开始 Then AI 自动补位且角色全局唯一（不与玩家重复）。

## Test-Refs
- `Tests.Godot/tests/UI/test_task54_new_game_menu_flow.gd`
