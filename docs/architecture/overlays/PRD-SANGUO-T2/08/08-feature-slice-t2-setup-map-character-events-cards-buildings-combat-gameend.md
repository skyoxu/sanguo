---
PRD-ID: PRD-SANGUO-T2
Title: 08-功能纵切-T2-开局配置与模块骨架（T50–T60）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0019
Arch-Refs:
  - CH01
  - CH02
  - CH04
  - CH05
  - CH06
  - CH07
  - CH10
---

# 08-功能纵切-T2-开局配置与模块骨架（T50–T60）

## 8.x.1 范围与目标

本页为 PRD-SANGUO-T2 在既有闭环基础上的“骨架扩展”纵切，目标是先锁死跨模块的不可回退口径，再逐模块填充，降低后期联动返工风险。

本页只描述功能纵切、契约口径与任务映射，不复制 CH01/CH02/CH03 的阈值与策略细节；安全、可观测性、质量门禁的单一事实来源仍以 Base 章节与 Accepted ADR 为准（特别是 ADR-0004/ADR-0019/ADR-0005）。

本阶段新增模块（骨架级）：
- 地图配置（多文件 + 索引）
- 新游戏配置界面（唯一开局入口）
- 角色（经济系数修饰器，已在 PRD 中追加）
- 随机事件池（事件格 + 每 N 回合全局事件）
- 行动卡（掷骰前窗口，止损版每回合最多 1 张）
- 建筑扩展（买地后建造，影响经济）
- 战斗模块（PVE，触发→回主循环）
- 每局胜利与结算界面（Core 判定，UI 展示）

## 8.x.2 统一口径（必须满足）

### 8.x.2.1 配置来源与只读约束（ADR-0019）

- 所有配置模板只允许从 `res://` 读取（例如地图/角色/事件/卡牌/建筑），禁止从绝对路径或 `user://` 读取配置模板。
- `user://` 仅用于运行时审计与存档（后续任务），不作为模板配置来源。

### 8.x.2.2 地图配置（多文件 + 索引）

- 地图列表索引：`res://Data/maps/_index.json`
  - 用于 UI 列表渲染，不扫描目录。
- 具体地图定义：`res://Data/maps/<map_id>.json`
  - `<map_id>` 与索引一致。
- Tile 语义最小集合：`city` / `pass` / `event` / `empty`。

### 8.x.2.3 开局配置唯一真相源（GameStartConfig）

开局必须由唯一配置对象（或等价结构）驱动，且可序列化为 JSON 审计快照，至少包含：
- `map_id`
- `players_count`：4–8（含玩家）
- `starting_money_preset`：5000/10000/20000
- `global_event_interval_turns`：5/10/20
- `random_seed`：用于事件与战斗确定性复现
- `character_assignments`：玩家先选，AI 补位随机；全局不允许同角色

### 8.x.2.4 经济修饰合成与 clamp（ADR-0004）

本阶段所有经济修饰统一采用“乘法链 + clamp + 0.5 步进”口径：
- 所有 multiplier 仅允许 0.5 步进（建议内部用 step int 表达：+1=+0.5）。
- 合成规则（唯一）：`effective_multiplier = clamp(character * building * event * action_card, 0.5, 3.0)`。
- 最终金额：`effective_value = base_value * effective_multiplier`。
- 过路费系数仅影响“地主收租侧”，不影响路人支付侧。

### 8.x.2.5 事件触发与行动卡窗口（ADR-0004）

- 行动卡窗口唯一：`TurnPhase.BeforeRoll`，止损版每回合最多 1 张（出 0/1）。
- 随机事件两类触发统一进入同一 RandomEventPool：
  - 事件格触发（落到 `event` tile）
  - 每 N 回合全局事件触发（N 属于 5/10/20）
- 同回合双触发的顺序必须固定且可测（以任务 T52 锁死）。

### 8.x.2.6 applied_multipliers 快照（ADR-0004）

所有经济相关域事件（买地/收租/月末结算/建造收益/事件应用）payload 必须包含 `applied_multipliers`，记录本次实际使用值：
- `character`
- `building`
- `event`
- `action_card`
- `effective`（clamp 后最终倍率）

UI 仅展示事件 payload/投影字段，不得在 UI 侧自行计算金额。

### 8.x.2.7 multiplier_step_delta 口径（整数步进）

- 事件、行动卡、建筑的效果输入统一采用 `multiplier_step_delta`（整数步进）表达：
  - `+1` 表示 `+0.5`
  - `-1` 表示 `-0.5`
  - `0` 表示不修改
- 该输入必须先映射为 multiplier 因子并纳入 8.x.2.4 的合成规则，再产出 `applied_multipliers` 快照。

## 8.x.3 契约与落盘位置（引用型）

契约 SSoT 落盘到 `Game.Core/Contracts/Sanguo/**`（不在本文复制字段定义）。本页仅要求：
- 事件命名遵循 ADR-0004（`core.sanguo.*`），禁止魔法字符串散落。
- 新增或扩展事件时，必须包含必要的关联字段与 `applied_multipliers` 快照（见上文）。

## 8.x.4 Taskmaster 任务映射（T50–T60）

本纵切与任务映射如下（按 Spine → Modules 顺序）：

- Spine（跨模块骨干）
  - Task 50：Spine: GameStartConfig 与可复现开局输入
  - Task 51：Spine: 倍率合成规则与 applied_multipliers 事件快照
  - Task 52：Spine: 回合窗口锁死（BeforeRoll 行动卡 0/1）与事件触发顺序

- Modules（8 个模块骨架）
  - Task 53：模块: 地图配置（多文件）与 Tile 语义
  - Task 54：模块: 新游戏配置界面（地图/人数/资金档/全局事件间隔/选角）
  - Task 55：模块: 角色配置（6角色）与初始资金口径
  - Task 56：模块: 随机事件池（事件格 + 每N回合全局事件）
  - Task 57：模块: 行动卡（BeforeRoll）止损版
  - Task 58：模块: 建筑扩展（买地后建造类型）
  - Task 59：模块: 战斗（PVE）触发与回主循环
  - Task 60：模块: 每局胜利与结算界面

## 8.x.5 测试对齐（引用型）

本纵切的测试对齐通过任务视图文件的 `acceptance[]` 与 `test_refs[]` 管理：
- `.taskmaster/tasks/tasks_back.json`（全量视图）
- `.taskmaster/tasks/tasks_gameplay.json`（玩法视图）

每条验收条款必须带 `Refs:` 指向对应的 xUnit/GdUnit4 测试文件；当新增本页范围内的任务或调整口径时，必须同步更新对应任务的 `acceptance[]` 与 `test_refs[]`，以保证“语义 → 证据链”可证伪。
