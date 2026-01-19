import re
from pathlib import Path


def main() -> int:
    prd_path = Path(".taskmaster/docs/prd.txt")
    text = prd_path.read_text(encoding="utf-8")

    marker_re = re.compile(
        r"\n=+\nPRD-TASK-SKELETON-DRAFT-T50-T60\n=+\n[\s\S]*\Z", re.M
    )

    new_block = """
====================
PRD-TASK-SKELETON-DRAFT-T50-T60
====================

本段为 T50–T60 的“任务拆解草案（骨架）”，用于提前暴露跨模块联动点，降低后期返工风险。
注意：本段只给出范围/非目标、确定性输入、事件 type+触发点、验收条款草案（ACC:Txx.n）与测试占位；事件字段细节与 Contracts 以 Overlay 08 与代码为准。

通用硬约束（不可回退）
- 配置模板只允许从 `res://Data/**` 读取（只读）；禁止扫描目录；存档只写 `user://`（后续任务）。
- 所有“经济数值计算”只在 Core 发生；UI 只展示事件/投影字段，不参与计算。
- 事件命名遵循 ADR-0004（CloudEvents-like `type`）：领域事件 `core.sanguo.*`；UI 事件 `ui.*`；Screen/状态切换 `screen.*`。
- 随机与可复现：任何随机选择都必须由 `random_seed` 驱动；同输入必须复现同输出。

确定性输入（本阶段统一）
- 地图索引：`res://Data/maps/_index.json`
- 地图定义：`res://Data/maps/<map_id>.json`
- 角色定义：`res://Data/characters.json`（6 角色，全局唯一不可重复）
- 随机种子：`random_seed`（新游戏配置阶段生成或输入；必须可审计/可回放）

事件与 DTO（仅列 EventType + 触发点，不展开字段）
- `core.sanguo.game.started`：新游戏配置完成并进入可玩主循环时。
- `core.sanguo.turn.started`：每回合开始。
- `core.sanguo.turn.advanced`：回合推进完成（从当前玩家切换到下一个玩家）。
- `core.sanguo.random_event.applied`：随机事件效果应用后。
- `core.sanguo.action_card.played`：行动卡在 BeforeRoll 窗口被使用后。
- `core.sanguo.building.built`：建造完成并对经济/状态产生影响后。
- `core.sanguo.battle.started` / `core.sanguo.battle.ended`：进入/退出 PVE 战斗场景时。
- `core.sanguo.game.ended`：满足胜利/失败条件并进入结算前。

- DTO: `GameStartConfig`：唯一开局输入快照（必须可序列化 JSON）。
- DTO: `AppliedMultipliers`：经济倍率快照（用于事件 payload；UI 只展示）。

任务骨架（T50–T60）

T50 Spine: GameStartConfig 与可复现开局输入
- 范围：定义唯一 `GameStartConfig`（map_id / players_count / starting_money_preset / global_event_interval_turns / random_seed / character_assignments），并以事件对外发布。
- 非目标：不做存档；不做 UI 美术与动画；不做角色成长。
- 验收：
  - ACC:T50.1 `GameStartConfig` 字段/范围/唯一性校验通过。
  - ACC:T50.2 地图列表仅从 `res://Data/maps/_index.json` 加载，不扫描目录。
  - ACC:T50.3 新游戏完成后发布 `core.sanguo.game.started`（含 `game_start_config` 与 `random_seed`）。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`
  - `Tests.Godot/tests/UI/test_task50_new_game_setup_flow.gd`

T51 Spine: 倍率合成规则与 applied_multipliers 事件快照
- 范围：统一倍率合成 `effective = clamp(character * building * event * action_card, 0.5, 3.0)`；并把“本次实际使用的倍率值”写入相关经济事件 payload（`applied_multipliers`）。
- 非目标：不引入复杂浮点档位（仅 0.5 步进）；不支持 UI 侧推导。
- 验收：
  - ACC:T51.1 任意组合输入下 `effective` 必须 clamp 到 [0.5, 3.0]，且只允许 0.5 步进。
  - ACC:T51.2 经济相关域事件 payload 必含 `applied_multipliers`（只读快照）。
  - ACC:T51.3 UI 事件日志仅展示事件里的倍率快照，不参与计算。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task51MultiplierCompositionTests.cs`
  - `Game.Core.Tests/Tasks/Task51AppliedMultipliersPayloadTests.cs`
  - `Tests.Godot/tests/UI/test_task51_hud_event_log_applied_multipliers.gd`

T52 Spine: 回合窗口锁死（BeforeRoll 行动卡 0/1）与事件触发顺序
- 范围：锁死回合阶段（至少含 BeforeRoll），止损版每回合最多使用 1 张行动卡（0/1）；并锁死“行动卡/事件触发/掷骰/移动/落点效果”的顺序。
- 非目标：不做多卡连锁；不做 PVP。
- 验收：
  - ACC:T52.1 BeforeRoll 窗口每回合只允许 0/1 张行动卡。
  - ACC:T52.2 同一回合内“事件格触发 + 每N回合全局事件”的顺序固定且可测。
  - ACC:T52.3 任何顺序相关事件都可从事件日志中复盘。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task52TurnWindowOrderingTests.cs`

T53 模块: 地图配置（多文件）与 Tile 语义
- 范围：多文件地图配置：索引 `_index.json` + 单图 `<map_id>.json`；Tile 最小集合：city / pass / event / empty；所有 tile 必含 name 用于 UI 展示。
- 验收：
  - ACC:T53.1 `_index.json` 可列出可用地图（id/name/path）。
  - ACC:T53.2 `<map_id>.json` 中每个 tile 有确定的 type 与 name；UI 能显示 name。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task53MapConfigTests.cs`

T54 模块: 新游戏配置界面（地图/人数/资金档/全局事件间隔/选角）
- 范围：新游戏界面作为唯一开局入口：选择 map、players_count(4-8)、starting_money_preset(5000/10000/20000)、global_event_interval_turns(5/10/20)、玩家角色；剩余席位由 AI 随机补位且不可重复。
- 验收：
  - ACC:T54.1 UI 可完成上述配置并进入游戏。
  - ACC:T54.2 AI 补位：角色全局唯一，不与玩家重复。
- Test-Refs（占位）：
  - `Tests.Godot/tests/UI/test_task54_new_game_menu_flow.gd`

T55 模块: 角色配置（6角色）与初始资金口径
- 范围：角色属于配置（只读）；只引入经济系数（starting_money_multiplier / buy_price_multiplier / toll_multiplier / income_multiplier）。
- 验收：
  - ACC:T55.1 角色配置可加载且 6 角色可展示。
  - ACC:T55.2 初始资金 = StartingMoneyPreset * starting_money_multiplier。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task55CharacterConfigTests.cs`
  - `Tests.Godot/tests/UI/test_task55_character_select_ui.gd`

T56 模块: 随机事件池（事件格 + 每N回合全局事件）
- 范围：事件格触发 + 每 N 回合全局事件统一进入 RandomEventPool；止损版事件效果仅允许 `multiplier_step_delta`（整型步进，1=+0.5）。
- 验收：
  - ACC:T56.1 事件格触发能从池中取出事件并应用。
  - ACC:T56.2 每 N 回合全局事件触发稳定可复现（由 seed 驱动）。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task56RandomEventPoolTests.cs`

T57 模块: 行动卡（BeforeRoll）止损版
- 范围：行动卡池（配置只读）；仅在 BeforeRoll 窗口可用；止损版每回合最多 1 张；效果仅 `multiplier_step_delta`。
- 验收：
  - ACC:T57.1 行动卡只允许 BeforeRoll 使用，且 0/1。
  - ACC:T57.2 使用行动卡后发布 `core.sanguo.action_card.played`，并影响本回合经济倍率快照。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task57ActionCardTests.cs`

T58 模块: 建筑扩展（买地后建造类型）
- 范围：买地后可选择建造类型（配置只读）；止损版只通过 `multiplier_step_delta` 影响经济；建造行为可审计（事件）。
- 验收：
  - ACC:T58.1 建造触发后发布 `core.sanguo.building.built`。
  - ACC:T58.2 建造效果只通过倍率快照进入经济计算。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task58BuildingsTests.cs`

T59 模块: 战斗（PVE）触发与回主循环
- 范围：落到指定 tile 或事件触发进入 PVE；完成后回到主循环；止损版战斗只要求“可进入、可退出、可复现”。
- 验收：
  - ACC:T59.1 触发战斗时发布 `core.sanguo.battle.started`。
  - ACC:T59.2 战斗结束后发布 `core.sanguo.battle.ended` 并返回主循环。
- Test-Refs（占位）：
  - `Tests.Godot/tests/E2E/test_task59_battle_enter_exit.gd`

T60 模块: 每局胜利与结算界面
- 范围：Core 判定胜利/失败（止损版先 1 条）；进入结算界面展示结果与关键统计；结算只展示不计算。
- 验收：
  - ACC:T60.1 满足条件时发布 `core.sanguo.game.ended` 并进入结算界面。
  - ACC:T60.2 结算界面展示 winner/原因/统计快照（来自事件或投影）。
- Test-Refs（占位）：
  - `Tests.Godot/tests/UI/test_task60_game_end_screen.gd`

""".lstrip("\n")

    m = marker_re.search(text)
    if not m:
        raise SystemExit("marker block not found: PRD-TASK-SKELETON-DRAFT-T50-T60")

    updated = text[: m.start()] + "\n" + new_block
    prd_path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Updated PRD skeleton block: {prd_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
