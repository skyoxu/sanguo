---
PRD-ID: PRD-SANGUO-T2
Title: 08-T50 GameStartConfig（唯一开局输入）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0019
Arch-Refs:
  - CH02
  - CH04
  - CH07
  - CH10
---

# T50：GameStartConfig（唯一开局输入）

本页描述 T50 的功能纵切口径与就地验收锚点（ACC）。契约命名与事件模型遵循 ADR-0004；安全与文件/资源基线遵循 ADR-0019；门禁与测试约束遵循 ADR-0005。

## 范围

- 定义 `GameStartConfig` 作为“新游戏”开局的唯一确定性输入，可用于审计与复盘。
- 完成“新游戏”入口流程后，进入主循环并发布 `core.sanguo.game.started`。

## 冻结口径（本阶段）

- `core.sanguo.game.started` 的事件 payload 顶层必须包含：`game_start_config` 与 `random_seed`。
- `random_seed` 必须可复用（同一输入→同一输出）；并且顶层 `random_seed` 与 `game_start_config.random_seed` 必须一致。
- `players_count` 仅允许 4–8；`starting_money_preset` 仅允许 5000/10000/20000；`global_event_interval_turns` 仅允许 5/10/20。
- 地图列表仅允许来自 `res://Data/maps/_index.json`，禁止扫描目录/枚举文件。

## 测试假设与默认值（冻结口径）

- Headless 的 GdUnit4 不可靠输入事件，测试应使用 `emit_signal("pressed")` 等方式触发 UI 行为。
- `Tests.Godot` 是独立 Godot 工程，`res://` 根指向 `Tests.Godot/`；因此若运行时逻辑读取 `res://Data/**`，测试工程必须提供对应数据镜像：`Tests.Godot/Data/**`。
- 由于“新游戏配置界面（地图/角色/参数）”尚未落地，本阶段胶水层使用最小默认开局配置（用于可玩度与门禁稳定性）：
  - `players_count = 4`
  - `starting_money_preset = 10000`
  - `global_event_interval_turns = 10`
  - `player_order = [p1, ai-1, ai-2, ai-3]`
  - 角色分配使用固定池并确保不重复（与 `players_count` 对齐）。
- 为避免“AI 自动推进”导致测试等待窗口被跳过，相关 GdUnit4 用例会将 `AiAutoAdvanceDelaySeconds` 与 `AiAutoAdvanceDelaySecondsWhenSkip` 调小（例如 0.05s）以降低抖动。

## 契约（EventType + 触发点）

- `core.sanguo.game.started`
  - 触发点：新游戏已根据 `GameStartConfig` 创建并进入可玩主循环后。
  - 事件 payload：顶层含 `game_start_config` 与 `random_seed`（用于复盘本次开局输入）。

## 验收条款（ACC）

- ACC:T50.1 `GameStartConfig` 字段/范围/唯一性校验通过：`map_id`、`players_count(4–8)`、`starting_money_preset(5000/10000/20000)`、`global_event_interval_turns(5/10/20)`、`random_seed`、`character_assignments(不重复且与 players_count 对齐)`。
- ACC:T50.2 地图列表仅从 `res://Data/maps/_index.json` 加载，不扫描目录。
- ACC:T50.3 完成“新游戏”入口流程后发布 `core.sanguo.game.started`，payload 顶层包含 `game_start_config` 与 `random_seed`。
- ACC:T50.4 `GameStartConfig` 可序列化为 JSON 审计快照并可反序列化回等价对象（字段值层面一致）。

## 示例（JSON）

- `docs/workflows/examples/gamestartconfig-canonical.example.json`

## Test-Refs

- `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`
- `Tests.Godot/tests/UI/test_task50_new_game_menu_started_event_payload.gd`
