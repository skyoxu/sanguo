# Prototype 工作流总览（中文）

说明：本文件整合了以下三份文档的内容，便于统一查阅与执行。
- docs/workflows/prototype-lane.md
- docs/workflows/prototype-lane-playbook.md
- docs/workflows/prototype-tdd.md

## 1. 概述与目的

- 目标：将探索性工作与正式交付工作隔离。
- prototype lane 不是另一个 `DELIVERY_PROFILE`。delivery profiles 用于控制“正式任务一旦进入交付，应当有多严格”；prototype lane 用于控制“这项工作是否应该进入正式的任务/评审/验收流水线”。

在 prototype lane 中，我们回答的问题是“这是否值得变成真正的工作？”，而不是“我们该如何把已经确定要交付的工作安全地交付？”。

## 2. 何时使用与不使用 prototype lane

应使用 prototype lane 的场景：
- 仍在验证以下问题是否值得继续：
  - 这个 mechanic 是否值得构建？
  - 这个 gameplay loop 是否足够有趣？
  - 这个 UI 交互是否容易理解？
  - 这个本地架构选项是否足够可行，值得晋升？
  - 这个 prompt/review 策略是否值得变成正式工作流？
- 希望先跑最小的代码与测试闭环，不准备把工作移入正式 `.taskmaster/tasks/*.json` 追踪。

不应使用 prototype lane 的场景：
- 工作已经是正式交付任务，
- 工作已经需要 acceptance refs、overlay refs 或 semantic review，
- 工作必须作为 Chapter 6 的交付证据，
- 工作已经明确应当进入 `run_review_pipeline.py`，
- 工作要对玩家发版（ships to players），
- 工作修改了长期兼容的存档格式，
- 工作将并入正式发布分支，
- 工作需要在 `.taskmaster/tasks/*.json` 中完成完整的任务条目，
- 或必须满足生产级的验收与评审门槛。

简短规则：
- prototype lane 回答“这是否应该变成真实工作？”
- 正式 Chapter 6 回答“如何安全地交付这项真实工作？”

## 3. 与 EA / Delivery Profiles / Chapter 6 的区别

- prototype lane
  - 关注：是否应当把探索结果转为真实工作。
  - 可能的结论：`discard` / `archive` / `promote`。
- `playable-ea / fast-ship / standard`（delivery profiles）
  - 关注：一旦进入正式交付，严格度如何。
  - 结果：在所选 profile 下，产出可发布或接近可发布的任务结果。
- 与 Chapter 6 的关系
  - prototype lane 不产生正式 Chapter 6 交付证据。
  - 一旦 `promote`，需要回到正式 Chapter 6（诸如 6.3 -> 6.4 -> 6.5 -> 6.6）的路径，遵循正确的 delivery-profile 与验收/评审要求。

## 4. 最小必需产物与推荐存放

每个 prototype 至少应记录：
- hypothesis（假设）
- core player fantasy（核心玩家幻想：玩家在一分钟内应该感受到什么）
- minimum playable loop（最小可玩循环：玩家能否端到端完成一次核心动作）
- scope boundary（范围边界：可用 `--scope-in`/`--scope-out` 体现）
- success criteria（成功标准）
- evidence links（证据链接：视频、笔记、截图、日志或基准小结）
- exit decision（退出决策）：`discard | archive | promote`

推荐位置：
- 设计为主的 prototype：`docs/prototypes/`
- 代码为主的 prototype：`prototypes/` 或功能本地的临时区域
- 新建 prototype 记录时，优先从模板开始：`docs/prototypes/TEMPLATE.md`

轻量 solo-dev 吸收规则：
- 只吸收“独立开发者快速闭环”的判断问题，不新增第二套执行引擎。
- 先问清楚核心玩家幻想、最小可玩循环、promote/archive/discard 的证据标准。
- 目标是让 prototype 更小、更可玩、更容易做退出决策，而不是提前做成完整正式任务。

注：完整操作流程见下文“Prototype Lane Playbook”。

## 5. Prototype TDD：目的与与正式 6.4/6.5/6.6 的差异

- 适用目的：工作仍在 `prototype lane`，但希望保持有纪律的 TDD 循环，验证 gameplay、UI、交互或本地架构实验是否值得保留。
- 可以跑 `red -> green -> refactor`。
- 不依赖 `.taskmaster/tasks/*.json`。
- 不依赖 acceptance refs、overlay refs 或 semantic review。
- 不会发布 `run_review_pipeline.py` 的 task recovery sidecars。
- 输出仅为 prototype 级别证据，不视为正式交付证据。
- 它不会消费 Taskmaster triplets、acceptance refs、overlay refs 或 review sidecars。
- 它适合 solo-dev 式的小闭环：先证明核心玩家幻想与最小可玩循环，再决定是否进入正式任务。

若 prototype 被 `promote`，必须通过正式路径重跑，不可将 prototype 证据当作生产证据：
- 可以回到 `6.3 -> 6.4 -> 6.5 -> 6.6` 的正式顺序，或使用下述推荐命令。

推荐的正式命令（示例）：
```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

## 6. Prototype TDD：稳定入口与常用脚本

- 创建原型场景脚手架（Day 2 推荐先跑）：
```powershell
py -3 scripts/python/dev_cli.py create-prototype-scene --slug <slug>
```

- 稳定入口（推荐）：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

- 低层脚本（TDD）：
```powershell
py -3 scripts/python/run_prototype_tdd.py --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```

- 低层脚本（场景脚手架）：
```powershell
py -3 scripts/python/create_prototype_scene.py --slug <slug>
```

## 7. Prototype TDD：最小用法与阶段语义

- 仅创建 prototype 记录：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --create-record-only --hypothesis "HUD loop readability is worth keeping"
```
结果：在 `docs/prototypes/` 下创建记录，并立即退出，不跑验证。
建议先参考或复制：`docs/prototypes/TEMPLATE.md`

建议在记录中尽早写清楚：
- 核心玩家幻想。
- 最小可玩循环。
- 什么证据足以让它 `promote`。
- 什么证据说明它应当 `archive` 或 `discard`。

- Prototype red：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```
默认行为与语义：
  - `red` 默认 `expect=fail`
  - 至少一个校验必须失败
  - 若所有校验通过，则标为 `unexpected_green`

- Prototype green：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```
默认行为与语义：
  - `green` 默认 `expect=pass`
  - 所有校验必须通过
  - 若仍有失败，则标为 `unexpected_red`

- Prototype refactor：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --stage refactor --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter HUDLoop
```
用途：在保留 prototype 的前提下清理临时代码，但不等同于正式交付完成，也不替代 Chapter 6。

- Godot/GdUnit 侧验证：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug ui-flow --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```
说明：
  - 仅在显式传入 `--gdunit-path` 时才会执行 GdUnit
  - 运行范围仅限你传入的 Godot 测试路径
  - `--gdunit-path` 需要 `--godot-bin`

- 常用参数摘要：
  - `--slug`：用于记录文件与日志路径的 prototype 名。
  - `--stage red|green|refactor`：TDD 阶段。
  - `--expect auto|fail|pass`：默认 `red=fail`，`green/refactor=pass`。
  - `--dotnet-target`：可重复的 `dotnet test` 目标。
  - `--filter`：对每个 `--dotnet-target` 应用的测试过滤表达式。
  - `--gdunit-path`：可重复的 Godot 验证路径。
  - `--create-record-only`：仅创建记录，不跑验证。
  - `--skip-record`：仅跑验证，不写记录。
  - `--related-task-id`：当未来的正式任务已知时，可提前记录其 id。

## 8. Prototype TDD：输出产物

每次 prototype TDD 运行会写入：
- prototype note：
  - `docs/prototypes/<date>-<slug>.md`
- summary：
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/summary.json`
- report：
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/report.md`
- 原始步骤日志：
  - `logs/ci/<date>/prototype-tdd-<slug>-<stage>/step-*.log`

## 9. Prototype Lane Playbook（端到端流程）

9.1 判断是否应走 prototype lane
- 仍在证明 mechanic 是否值得做；
- 仍在测试 UI/交互是否可理解；
- 仍在评估本地架构选项；
- 想先获得最小代码与测试闭环；
- 暂不准备纳入 `.taskmaster/tasks/*.json` 正式追踪。

若以下任一为真，则不应使用 prototype lane：
- 已是正式交付任务；
- 已需要 acceptance refs、overlay refs 或 semantic review；
- 必须为 Chapter 6 提供交付证据；
- 已准备好进入 `run_review_pipeline.py`。

简短规则：
- prototype lane 回答“应不应该成为真实工作？”
- 正式 Chapter 6 回答“如何安全交付已确定的工作？”

9.2 建议顺序（red/green/refactor 思路）
1) 写下 hypothesis。
2) 写下核心玩家幻想与最小可玩循环。
3) 创建 prototype 记录。
4) 跑 prototype red。
5) 实现最小代码改动。
9.2A Solo-dev playtest check
- Before deciding, run a short hands-on check:
- Is the core player fantasy visible within the first minute?
- Can the minimum playable loop be completed without explanation?
- Is the next decision clearly `promote`, `archive`, or `discard`?
- This is a lightweight prototype check, not a formal Chapter 6 QA gate.
6) 跑 prototype green。
7) 仅在需要时跑 prototype refactor。
8) 对交互/玩法类 prototype 做一次轻量试玩或可读性检查。
9) 决策 `discard | archive | promote`。
10) 若为 `promote`，回到正式 Chapter 6 流程。

9.3 创建 prototype 记录（命令与字段）
- 推荐命令：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --create-record-only --hypothesis "<what are you proving>"
```
- 建议尽早填写的字段：
  - `--hypothesis`
  - 核心玩家幻想
  - 最小可玩循环
  - `--scope-in`
  - `--scope-out`
  - `--success-criteria`
  - `--next-step`
- 示例：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-loop --create-record-only --hypothesis "HUD loop readability is worth keeping" --scope-in "HUD tick loop" --scope-out "formal task refs" --success-criteria "The core player fantasy is visible within the first minute" --success-criteria "A green test proves the minimum playable loop is understandable enough to keep"
```
- 产物：`docs/prototypes/<date>-<slug>.md`

9.4 跑 prototype red（按需选择 C# 或 Godot）
- 纯 C#：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```
- Godot / GdUnit：
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

9.5 实现最小变更并跑 prototype green
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```
心智模型：
- red 证明“当前还未实现/不可用”
- green 证明“在当前小范围内可行/可保留”

9.6 仅在需要时跑 prototype refactor
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage refactor --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>
```
适用场景：打算保留 prototype 一段时间，清理临时代码，同时保留 prototype 级验证。
不等同于正式交付完成，也不替代 Chapter 6。

9.7 做一次轻量试玩或可读性检查
- 核心玩家幻想是否能在第一分钟内被感受到？
- 最小可玩循环是否能在没有额外解释的情况下完成？
- 下一轮迭代是否明显值得正式化，还是仍然过于模糊？

这一步是轻量 solo-dev 检查，不是正式 Chapter 6 QA 门禁。

9.8 阅读输出并做决策
- `discard`：玩法不够有趣、不够清晰，或继续探索的性价比已经很低，停止。
- `archive`：方向有信号，但循环还不够强，不足以进入正式任务；保留证据以便以后比较。
- `promote`：核心玩家幻想已清楚，最小可玩循环已能端到端跑通，下一步正式任务交付内容已经明确。

对应产物位置参见“Prototype TDD：输出产物”。

9.9 Promote 之后的动作（回到正式交付）
- 不要把 prototype 产物当作正式交付结果继续使用。
- 切换回正式路径：
  1) 创建正式任务条目（`.taskmaster/tasks/*.json`）。
  2) 增加 task refs、acceptance refs、overlay refs。
  3) 必要时补充 execution-plan / decision-log。
  4) 回归 Chapter 6，走正确的 delivery-profile 与评审路径。
- 推荐正式命令（示例）：
```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

9.10 实用命令模板
- 模板 A：小型纯 C# mechanic
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --create-record-only --hypothesis "Combo rule is worth keeping"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter ComboRule
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug combo-rule --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter ComboRule
```
- 模板 B：UI / Godot 交互
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --create-record-only --hypothesis "HUD flow is understandable enough to keep"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --stage red --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug hud-flow --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```
- 模板 C：先 C# 后 Godot 验证
```powershell
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --create-record-only --hypothesis "Target selection flow is worth promoting"
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter TargetSelection
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage green --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter TargetSelection
py -3 scripts/python/dev_cli.py run-prototype-tdd --slug target-selection --stage green --godot-bin "$env:GODOT_BIN" --gdunit-path tests/UI
```

9.11 常见错误
- 用 prototype lane 替代正式交付流程；
- 把 prototype red/green 当作 Chapter 6 交付证据；
- 在 prototype lane 里新增一套与现有脚本竞争的执行引擎；
- 在 prototype 中更改长期域边界（如长寿命 contracts）却不创建正式后续工作；
- 在工作已明确是产品正式工作时仍停留在 prototype lane。

9.12 快速决策树
- 问题仍是“这是否值得做”？是 → 用 prototype lane；否则 → 直接走正式 Chapter 6。
- 探索中仍想保留 TDD？是 → 使用 `run-prototype-tdd`。
- 核心玩家幻想清楚，最小可玩循环端到端成立？是 → 选 `promote` 并回到正式任务流。
- 结果有部分参考价值但循环不够强？→ 选 `archive`。
- 结果表明方向错误，或继续探索性价比很低？→ 选 `discard`。

## 10. 允许的放宽与仍需坚持的硬边界

允许在 prototype lane 放宽：
- 完整 `run_review_pipeline.py` 使用要求，
- 完整 semantic review 严格度，
- 完整验收用例撰写，
- 完整任务 triplet 集成，
- 发布级覆盖率目标。

但仍需坚持的硬边界（不可放宽）：
- 不得超出现行安全基线进行不安全的路径/主机/网络行为，
- 不得在 `Game.Core/Contracts/**` 发生无声漂移（silent drift），
- 不得把 prototype 冒充为完成的正式任务，
- 不得在没有“晋升（promotion）”步骤时将一次性实验代码混入长期模块，
- 不得把 prototype 的技术债隐藏到生产文件中而不做明确的后续计划。

## 11. Promotion 规则与正式化要求

仅当 prototype 有明确“保留（keep）”的结论后，才可将其 `promote` 到正式交付。

良好的 `promote` 通常意味着：
- 核心玩家幻想已经足够清楚，值得保留。
- 最小可玩循环可以端到端执行。
- 下一步正式任务比剩余 prototype 不确定性更清晰。

良好的 `archive` 通常意味着：
- 想法仍有信号。
- 但循环还不够强，不足以进入正式任务。
- 保留证据对后续比较仍有价值。

良好的 `discard` 通常意味着：
- 循环不够有趣、不够清晰或不可行。
- 继续迭代很难以低成本改变结论。

Promotion 时应补充或更新：
- 在 `.taskmaster/tasks/*.json` 中创建/更新正式任务条目，
- 补充 overlay refs / test refs / acceptance refs，
- 若 prototype 变更了域边界，则更新正式 contracts，
- 增加确定性的测试，并走正确的 delivery-profile 评审路径。

切记：prototype 的证据不能直接当作生产证据。晋升后应当按正式 Chapter 6 要求重跑（可参见上文推荐的正式命令与 6.3 -> 6.4 -> 6.5 -> 6.6 的顺序）。

## 12. 简要操作流程（与 Playbook 对应）

- 写下 hypothesis、核心玩家幻想与最小可玩循环。
- 仅运行维持仓库安全所需的最小检查。
- 做一次轻量试玩或可读性检查。
- 尽快做出 `discard | archive | promote` 决策。
- 若决定 `promote`，请将结果重写或迁移到正式任务流水线，而不是把 prototype 产物当作已完成项。
