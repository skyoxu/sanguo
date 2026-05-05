# Prototype 7天可玩 Godot 原型执行模板（中文）

本文档用于指导新仓在仍处于玩法验证阶段时，不进入 `workflow.md` 第五章和第六章，而是通过 prototype lane 和 prototype TDD 尽快做出一个能玩、能判断是否值得继续的 Godot 原型。

## 0. 顶层路由编排器（推荐入口）

如果你希望按 7 天原型流程推进，但又不想一开始就手动拼命令，推荐优先使用顶层入口：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-prototype-file>.md
```

这个入口只覆盖 Day 1 到 Day 5，并且是轻量编排，不会引入 `workflow.md` 第五章、第六章那套正式任务 harness。

### 0.1 可接受的输入来源

支持两种输入方式：

1. 直接传 `--prototype-file`
   - 文件内容应遵循 `docs/prototypes/TEMPLATE.md` 或 `docs/prototypes/TEMPLATE.zh-CN.md`
2. 不传文件，直接用 `--set key=value` 逐步补充
   - 适合你还没建原型文件，只想先从 CLI 里把关键信息喂给路由器

例如：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --set slug=combat-loop --set hypothesis="验证战斗循环是否值得继续" --set core_player_fantasy="玩家在第一分钟内感受到战斗节奏" --set minimum_playable_loop="进入场景并完成一次攻击反馈" --set success_criteria="玩家可以完成一次最小可玩循环,试玩后仍愿意继续"
```

### 0.2 必填项与默认值

以下字段是必填项；缺任何一个，路由器都会暂停，不会继续进入 Day 1 之后的步骤：

- `slug`
- `hypothesis`
- `core_player_fantasy`
- `minimum_playable_loop`
- `success_criteria`
- `game_feature`
- `core_gameplay_loop`
- `win_fail_conditions`

以下字段如果没填，会自动使用系统默认值，不要求你第一次就补齐：

- `status=active`
- `owner=operator`
- `date=<today>`
- `related_formal_task_ids=["none yet"]`
- `scope_in=["TBD"]`
- `scope_out=["TBD"]`
- `promote_signals=["TBD"]`
- `archive_signals=["TBD"]`
- `discard_signals=["TBD"]`
- `evidence=["TBD"]`
- `decision=pending`
- `next_step="Proceed to the next prototype workflow confirmation step."`

建议口径是：先把必填项写准，再逐步细化默认值字段，而不是在玩法尚未证明前把文档写得过重。

### 0.2.1 BMAD/GDS Game Type Guide Integration

The top-level router absorbs the useful parts of BMAD/GDS `gds-create-gdd` Step 2 and Step 7, but only for prototype lane intake. It does not enter the full 14-step GDD workflow.

- Step 2 reuse: load the matching game type guide from known `Game Type` metadata and use it to capture the core game concept.
- Step 7 reuse: each game type has different design focus areas; prototype lane only uses the parts relevant to the minimum playable loop.
- Template source: `.agents/skills/gds-create-gdd/game-types/`, extracted into `docs/game-type-guides/`.
- Index source: `docs/game-type-guides/game-types.csv`, with 24 canonical game type ids.

When `AGENTS.md` or `README.md` contains `## Game Project Metadata`, load `docs/game-type-guides/<canonical-id>.md` as question and scoring context. Do not copy the full guide into the prototype record.

Step 7 is consumed as `Step07-lite`:

- Parse the matching guide by `###` sections and `{{placeholder}}` markers.
- Select at most three sections relevant to the smallest playable loop.
- Ask only for `game_type_specifics.<section_id>` answers, not the full GDD Step 7 chapter.
- Persist answers under `## Game Type Specifics` in the prototype record.
- Surface the captured guide path, section titles, and answers in `project-health` after the next scan.

### 0.3 暂停与确认机制

这个入口不是“拿到信息就一路跑到底”。它在以下场景会主动暂停：

- 没传 `--prototype-file`，且也没有足够的 `--set`
- 原型文件里缺少必填项
- 必填项齐了，但你还没有用 `--confirm` 明确确认
- 即将进入 Day 5，但没有传 `--godot-bin`

暂停时会输出下一步动作，并写一份轻量恢复状态：

```text
logs/ci/active-prototypes/<slug>.active.json
```

这份 active state 只记录 prototype 路由所需的最小信息，用来防止上下文压缩后你又得重新整理原型目标，但不会做成正式 Chapter 6 那种重 sidecar。

### 0.3.1 Core Gameplay Triple Pause

After the base prototype fields are complete, the router must pause in sequence for three player-provided core gameplay fields:

1. `game_feature`: define core gameplay - game feature
2. `core_gameplay_loop`: define core gameplay - core gameplay loop
3. `win_fail_conditions`: define core gameplay - win/fail conditions

These pauses are one-way data capture, not approval forks. Any non-empty user input can continue to the next route step. The router saves the original input for `docs/prototypes/<date>-<slug>.md`, `logs/ci/active-prototypes/<slug>.active.json`, and the project-health page.

### 0.4 推荐执行节奏

1. 先准备 `docs/prototypes/<your-file>.md`，按模板填写。
2. 运行：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-file>.md
```

3. 路由器会先整理关键信息并暂停，等待你确认。
4. 你确认无误后，再继续：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-file>.md --confirm --godot-bin "$env:GODOT_BIN"
```

5. 如果中途会话断了，或者 Codex 上下文被压缩，可通过轻量恢复状态继续：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --resume-active <slug>
py -3 scripts/python/dev_cli.py run-prototype-workflow --resume-active <slug> --confirm --godot-bin "$env:GODOT_BIN"
```

### 0.5 这个路由器实际做什么

它会按顺序推进到以下节点，并在 Day 5 停止：

- Day 1：确保 prototype record 存在
- Day 2：创建最小 Godot 原型场景脚手架
- Day 3：跑 prototype red
- Day 4：跑 prototype green
- Day 5：跑 Godot / GdUnit 侧验证

它不会替你进入 Day 6 的试玩判断和 Day 7 的 promote / archive / discard 决策。那两天仍然需要你基于证据做人工判断。

### 0.6 进入 TDD 前的原型信息评分

当必填信息已经齐全后，路由器不会立刻进入 TDD，而是先生成一份面向“小工作室独立游戏原型验证”的 intake score，并暂停等待用户确认。

这不是 PRD/GDD 完整度审查，不要求完整世界观、完整系统设计、长期路线图或正式架构。它分成两层：

1. 硬评分：判断这份文件是否足够支撑顶层路由编排器继续推进 Day 1 到 Day 5。
2. AI 软评分：基于文件内容，对市场潜力和商业化成本做保守判断。

默认只跑硬评分，不调用大模型。

#### 0.6.1 硬评分（deterministic，50 分）

硬评分只回答一个问题：这份信息是否足够让小团队开始做一个短周期、可玩的 Godot 原型。

共 2 个维度，每项 25 分：

- `prototype_feasibility`：这份文件是否足够具体，能让顶层路由编排器推进 prototype lane，而不是在 Day 2 到 Day 5 期间持续卡在模糊描述上。
- `content_completeness`：这份文件是否把假设、核心玩家幻想、最小可玩循环、成功标准、退出信号和下一步写到了足够支撑原型验证的程度。

默认只跑这部分：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-file>.md
```

#### 0.6.2 AI 软评分（codex，50 分）

如果你希望在硬评分之外，让 Codex 基于文件内容给一次更偏产品判断的软审查，可以显式开启：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-file>.md --score-engine codex
```

AI 软评分只评 2 个维度，每项 25 分：

- `market_potential`：仅根据文件里写出来的内容，判断这个想法是否呈现出明确受众、差异化卖点、继续游玩的吸引力。
- `commercialization_cost`：仅根据文件里写出来的内容，判断这个 prototype 如果后续进入商业化，当前范围控制、内容规模和实现负担是否仍然现实。

或者同时保留硬评分，并附加 Codex second opinion：

```powershell
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file docs/prototypes/<your-file>.md --score-engine hybrid
```

建议：

- 日常默认用 `deterministic`，只看“能否推进 prototype 流程”，速度快、稳定、无模型成本。
- 当你希望脚本额外告诉用户“这个想法看起来有没有市场潜力、商业化成本是否偏高”时，再用 `codex`。
- `hybrid` 适合在一个摘要里同时看到“流程可行性硬分”和“市场/商业化软分”。
- Codex 评分是软建议，不替代硬评分，也不要求你把 prototype 文档补成 PRD/GDD。
- 用户确认评分摘要后，才继续加 `--confirm` 进入 Day 1 到 Day 5。

## 1. 适用前提

适用于以下情况：

- 还在验证玩法本身是否值得做
- 还不想启用 `.taskmaster/tasks/*.json` 正式跟踪
- 还不想填 acceptance refs / overlay refs / semantic review
- 目标是先做出“可实际操作”的 Godot 原型，再决定是否 promote

不适用于以下情况：

- 已经是正式交付任务
- 已经需要正式 acceptance / review 门禁
- 已经需要作为 Chapter 6 证据链的一部分

## 2. 核心原则

这个阶段要做的不是“做正式产品”，而是“快速验证这个想法值不值得继续”。

因此优先级是：

1. 可玩：先让核心玩家幻想能被实际感受到
2. 可闭环：最小可玩循环能端到端完成
3. 可验证：至少有 prototype red/green 或实际试玩证据
4. 可做出 discard / archive / promote 决策
5. 可以在后续 promote 时迁移回正式流程
6. 最后才是架构优雅性

## 3. 推荐目录结构

建议先把 prototype 与正式模块分开，不要一开始就把实验代码放进长期模块。

```text
Game.Godot/Prototypes/<slug>/
  <SlugPascalCase>Prototype.tscn
  Scripts/
  Assets/
Tests.Godot/tests/Prototype/<Slug>/
docs/prototypes/
```

例子：

```text
Game.Godot/Prototypes/combat-loop/
  CombatLoopPrototype.tscn
  Scripts/
    CombatLoopPrototype.cs
    EnemyDummy.cs
Tests.Godot/tests/Prototype/CombatLoop/
docs/prototypes/2026-04-15-combat-loop.md
```

## 4. 命名建议

- slug：`combat-loop`、`hud-flow`、`target-selection` 这种短横线命名
- 场景名：`<SlugPascalCase>Prototype.tscn`
- 脚本名：`<SlugPascalCase>Prototype.cs`、`EnemyDummy.cs` 等
- C# 测试名仍建议遵循 `ShouldX_WhenY`

## 5. 7天执行节奏

### Day 1：建原型记录，明确假设

目标：先写明要验证什么，而不是盲目写代码。此时还要写清楚核心玩家幻想和最小可玩循环：前者说明玩家应该感受到什么，后者说明玩家至少能完成哪一个端到端动作。

建议先复制并填写模板：`docs/prototypes/TEMPLATE.md`

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --create-record-only --hypothesis "核心战斗循环值得继续做" --scope-in "移动、攻击、受击反馈、简单敌人" --scope-out "正式 task refs、acceptance refs、overlay refs、正式 review" --success-criteria "玩家可以完成一次完整战斗循环" --success-criteria "试玩后仍认为值得继续做" --next-step "先做最小可操作场景"
```

产物：

- `docs/prototypes/<date>-combat-loop.md`

Day 1 的记录里建议至少能回答：

- 核心玩家幻想是什么？
- 最小可玩循环是什么？
- 什么证据说明这个 prototype 值得 `promote`？
- 什么证据说明它应该 `archive` 或 `discard`？

### Day 2：做出最小可操作场景

目标：在 Godot 中做出一个可进入、可操作、可完成最小玩法循环的 prototype scene。重点不是“做大”，而是把 Day 1 写下的核心玩家幻想变成一个玩家可以亲手操作的最小闭环。

建议先运行脚手架命令，生成最小 `.tscn` 场景和对应 C# stub：

```powershell
py -3 scripts/python/dev_cli.py create-prototype-scene --slug combat-loop
```

默认会创建：

```text
Game.Godot/Prototypes/combat-loop/
  CombatLoopPrototype.tscn
  Scripts/CombatLoopPrototype.cs
  Assets/
```

如果你确认这个 prototype 更适合 `Node2D` 根节点，也可以显式指定：

```powershell
py -3 scripts/python/dev_cli.py create-prototype-scene --slug combat-loop --scene-root Node2D
```

建议最少包含：

- 玩家节点
- 一个敌人假体或交互目标
- 最简单的输入
- 最简单的反馈
- 一个可重复进入和重置的原型场景

建议当天必须回答的 4 个问题：

- 玩家进入场景后，10 到 30 秒内能否开始操作？
- 玩家能否完成一次最小可玩循环？
- 反馈是否足以让玩家知道“自己刚刚做成了什么”？
- 如果失败，能否快速重试，而不是卡死在场景里？

成功标准：

- 场景可以在 Godot Editor 中稳定打开并运行。
- 至少存在一条从“进入场景”到“完成一次核心动作”的可操作路径。
- 玩家输入、目标状态变化、反馈三者之间已经形成最小闭环。
- 你可以用一句话描述这个场景怎样体现核心玩家幻想。

失败信号：

- 场景能打开，但玩家无法开始操作。
- 能操作，但无法完成一次最小可玩循环。
- 完成动作后缺少明确反馈，无法判断是否成功。
- 为了让场景跑起来，开始引入大量正式系统、正式架构或长期模块耦合。

当天收口产物：

- `Game.Godot/Prototypes/<slug>/` 下至少有一个可在 Godot Editor 中打开运行的 `.tscn` 场景。
- 这个场景最好来自 `create-prototype-scene` 脚手架，再由你补上最小可玩循环。
- 如有必要，补一张截图或一段短视频到 `docs/prototypes/<date>-<slug>.md` 的 Evidence。
- 在 prototype 记录里更新 `Next Step`，明确 Day 3 要钉住哪一个最关键的 red 测试。

这一天的验证以 Godot Editor 实际运行场景为主，不追求完整体系。

### Day 3：补最关键的 C# 小测试，跑 red

适合先钉住的内容：

- 状态切换
- 攻击 cooldown
- 目标选择
- 伤害结果

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter CombatLoop
```

成功标准：

- 至少一条验证失败
- prototype red 是有效的，而不是 `unexpected_green`

### Day 4：做最小实现，跑 green

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter CombatLoop
```

成功标准：

- 关键测试通过
- 在 Godot 场景中可以完成一个最小玩法循环

### Day 5：如果重点是交互，补 Godot / GdUnit 验证

如果这个原型重点是 HUD、UI、节奏或场景交互，可以单独补一小组 Godot 验证路径：

```text
Tests.Godot/tests/Prototype/CombatLoop/
```

red:

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/Prototype/CombatLoop
```

green:

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/Prototype/CombatLoop
```

这一天适合验证：

- HUD 是否出现
- 交互输入后 UI 是否更新
- 最小场景操作流是否成立

### Day 6：实际试玩，记录证据

这一天不再优先增加功能，而是进入“这个方向值不值得继续做”的判断阶段。

建议收集：

- 实际试玩视频
- 截图
- prototype summary / report
- 自己的观察笔记

轻量试玩/可读性检查问题：

- 核心玩家幻想是否能在第一分钟内被感受到？
- 玩家是否能在没有额外解释的情况下完成最小可玩循环？
- 操作、反馈、HUD 或场景提示是否足够清楚？
- 下一轮是否明显值得正式化，还是仍然只适合继续探索？

重点读取产物：

- `docs/prototypes/<date>-<slug>.md`
- `logs/ci/<date>/prototype-tdd-<slug>-red/summary.json`
- `logs/ci/<date>/prototype-tdd-<slug>-green/summary.json`
- `logs/ci/<date>/prototype-tdd-<slug>-*/report.md`

### Day 7：做出退出决策

只允许三种结果：

- `discard`：玩法不够有趣、不够清晰，或继续探索的性价比已经很低，停止
- `archive`：方向有信号，但循环还不够强，不足以进入正式任务；保留证据以便以后比较
- `promote`：核心玩家幻想已清楚，最小可玩循环已能端到端跑通，下一步正式任务交付内容已经明确

如果结果是 `promote`，后续再进入正式流程：

1. 创建正式 task
2. 补 task refs / acceptance refs / overlay refs
3. 需要时补 execution-plan / decision-log
4. 再切入 Chapter 6

## 6. 这个阶段不需要做的事

既然目标是“先做出可玩原型”，那么先不要做这些：

- 不建 `.taskmaster/tasks/*.json`
- 不补 acceptance refs
- 不补 overlay refs
- 不跑 `run_review_pipeline.py`
- 不跑 `llm_review_needs_fix_fast.py`
- 不把 prototype red/green 当成 Chapter 6 正式证据
- 不新增第二套和现有 workflow 竞争的执行引擎

## 7. 常用命令模板

### Day 1

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --create-record-only --hypothesis "核心战斗循环值得继续做" --scope-in "移动、攻击、受击反馈、简单敌人" --scope-out "正式 task refs、acceptance refs、overlay refs、正式 review" --success-criteria "核心玩家幻想能在第一分钟内被感受到" --success-criteria "玩家可以完成一次最小可玩循环"
```

### Day 3 red

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter CombatLoop
```

### Day 4 green

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter CombatLoop
```

### Day 5 Godot red

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/Prototype/CombatLoop
```

### Day 5 Godot green

```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combat-loop --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/Prototype/CombatLoop
```

## 8. 一句话总结

如果你的目标只是“先做出一个能玩的 Godot 原型”，那么正确做法是：用 prototype lane 管边界，用 `run-prototype-tdd` 做最小 red/green 闭环，用 Godot 场景实际试玩，确认核心玩家幻想和最小可玩循环是否成立，并尽快做出 `discard | archive | promote` 决策。若最终 `promote`，必须回到正式 Chapter 6，不要把 prototype 证据当成正式交付证据。

## 9. 最佳使用提示词（给 Codex / AI 代理）

如果你想让 Codex 或其他 AI 代理严格按 prototype lane 执行，而不是误入正式 Chapter 5 / Chapter 6，可以直接使用下面这份提示词：

```text
先读 AGENTS.md、docs/agents/00-index.md、docs/workflows/prototype-lane.md、docs/workflows/prototype-tdd.md，并以 docs/workflows/prototype-7day-playable-godot-zh.md 为当前原型执行准则。

当前工作仍处于 prototype lane，不进入 workflow.md 第五章和第六章，不创建正式 task refs / acceptance refs / overlay refs，不跑 run_review_pipeline.py。

默认优先使用顶层原型入口：
py -3 scripts/python/dev_cli.py run-prototype-workflow --prototype-file <path-to-prototype-file>

执行要求：
1. 先读取 prototype 文件，并按 docs/prototypes/TEMPLATE.md 或 TEMPLATE.zh-CN.md 解释字段。
2. 先判断信息是否完整：
   - 必填项只有：slug、hypothesis、core_player_fantasy、minimum_playable_loop、success_criteria。
   - 其他字段可先接受系统默认值，不要为了补齐非关键字段阻断工作。
3. 一旦信息不足、文件不存在、或需要进入下一步但缺少必要参数，必须暂停并明确告诉我缺什么；不要脑补，不要自行继续。
4. 如果信息完整，也不要直接执行 Day 1 到 Day 5；先生成“小工作室独立游戏原型验证”评分摘要，确认它不是 PRD/GDD 完整度审查，再等待我确认。
5. 默认使用确定性评分；只有我明确要求时，才加 `--score-engine codex` 或 `--score-engine hybrid` 做 Codex 软评分。
5. 如果会话中断、上下文被压缩或需要恢复，优先使用：
   - py -3 scripts/python/dev_cli.py run-prototype-workflow --resume-active <slug>
   不要依赖聊天历史脑补恢复。
6. 只执行到 Day 5：
   - Day 1 建 prototype record
   - Day 2 建最小可操作 Godot 场景
   - Day 3 跑 red
   - Day 4 跑 green
   - Day 5 跑 Godot / GdUnit 验证
   Day 6 和 Day 7 只做建议，不自动执行最终 promote / archive / discard 决策。
7. 所有结论都围绕两件事：核心玩家幻想是否成立、最小可玩循环是否成立。
8. 文档读写和记录统一使用 Python + UTF-8。
9. 每完成一天，都要明确输出：
   - 今天完成了什么
   - 产物在哪里
   - 下一天进入条件是否满足
   - 目前更像是 promote、archive 还是 discard
```

这份提示词的核心目标只有一个：让代理始终停留在“验证玩法是否值得继续”的语境里，而不是提前滑入正式交付工作流。
