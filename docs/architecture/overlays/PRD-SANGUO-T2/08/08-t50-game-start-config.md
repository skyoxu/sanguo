---
PRD-ID: PRD-SANGUO-T2
Title: 08-T50 GameStartConfig（唯一开局输入）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0019
Arch-Refs:
  - CH01
  - CH02
  - CH06
---

# T50：GameStartConfig（唯一开局输入）

本页为 T50 的功能纵切拆页，统一口径与契约清单见 `08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md`。

## 范围
- 定义唯一开局配置对象（或等价结构）`GameStartConfig`，作为“新游戏”的唯一输入快照，可序列化为 JSON 用于审计/回放。
- UI 新游戏配置界面完成配置后，进入主循环并发布 `core.sanguo.game.started`（或等价事件）。

## 非目标
- 不实现存档系统（写入/读回 `user://` 属于后续任务）。
- 不做目录扫描与资源发现（只读取明确路径的 `res://Data/**`）。

## 确定性输入
- 地图索引：`res://Data/maps/_index.json`
- 地图定义：`res://Data/maps/<map_id>.json`
- 角色定义：`res://Data/characters.json`
- `random_seed`：驱动 AI 补位、事件抽取、战斗随机等（同输入必须复现同输出）

## 契约（EventType + 触发点）
- `core.sanguo.game.started`：新游戏配置完成、GameStartConfig 被固化并进入主循环时。

## 验收条款（ACC）
- ACC:T50.1 `GameStartConfig` 字段/范围/唯一性校验通过（至少含：map_id、players_count(4-8)、starting_money_preset(5000/10000/20000)、global_event_interval_turns(5/10/20)、random_seed、character_assignments(全局唯一)）。
- ACC:T50.2 地图列表仅从 `res://Data/maps/_index.json` 加载，不扫描目录。
- ACC:T50.3 新游戏完成后发布 `core.sanguo.game.started`，payload 含 `game_start_config` 与 `random_seed`。

## Test-Refs
- `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`
- `Tests.Godot/tests/UI/test_task50_new_game_setup_flow.gd`

