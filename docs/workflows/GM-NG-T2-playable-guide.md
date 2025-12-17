# 从 GM/NG 任务驱动首个 T2 场景实现

> 本文档总结当前对话中关于“如何从 GM/NG 任务驱动首个 T2 场景实现”的建议，作为 newguild 项目的工作流参考。

## 1. 先用 PRD + Overlay 锁定 T2 场景流

- 在 `docs/prd.txt` 中，找到你补充的“最小 T2 Playable 场景流”段落，明确：
  - 启动 → 进入哪个 Guild Manager 场景；
  - 完成一轮 Week/Phase 的切换；
  - 场景结束或返回菜单的方式。
- 在 Overlay：
  - 打开 `docs/architecture/overlays/PRD-Guild-Manager/08/08-功能纵切-公会管理器.md`，确认 T2 流程已被引用（而不是重复阈值或策略）。
- 在 Checklist：
  - 查看 `docs/architecture/overlays/PRD-Guild-Manager/08/ACCEPTANCE_CHECKLIST.md`，确保存在一条描述“首个 T2 Playable 场景流”的验收条款。

## 2. 基于完整 T2 的最小任务清单与顺序

根据 `.taskmaster/tasks/tasks_back.json` 与 `tasks_gameplay.json` 中的 `depends_on`，首个 T2 Playable 场景在 Taskmaster 语义下的最小依赖闭包为 6 个任务：

1. **NG-0001** —— newguild 首个纵切 PRD ↔ Overlay 映射
   - 为 Guild Manager 核心循环建立一份“可落地”的 PRD 片段与 overlays/08 映射。
2. **NG-0020** —— Guild Manager 首个三层垂直切片骨架
   - 在 Game.Core / Game.Godot / Tests.Godot 三层搭好与公会管理器相关的基础骨架与命名归属。
3. **NG-0012** —— Python 版 headless smoke（strict 模式）
   - 把 `scripts/python/smoke_headless.py` 等脚本打通，能在 Windows/headless 下用 strict 模式跑最小烟测。
4. **NG-0021** —— 首个垂直切片的 xUnit/GdUnit4/smoke + CI 串联
   - 让首个 Guild Manager 垂直切片（包括 T2 流程）进入 dev_cli / CI 流水线，形成最小的“测试 + smoke + 日志”闭环。
5. **GM-0101** —— EventEngine Core（事件引擎）
   - 在 Game.Core 中实现公会管理器所需的事件引擎骨干，对 Resolution / Player / AI Simulation 三个阶段给出可测行为。
6. **GM-0103** —— GameTurnSystem + T2 回合/时间推进
   - 把 PRD 里的 Week/Phase 流程映射成 GameTurnSystem 可管理的状态机，并在 Godot 场景里通过 UI 显示和交互驱动一轮 T2 流程。

简单理解：

- NG-0001/0020/0012/0021：保证这条 T2 流程在 **文档/架构/测试/CI** 层是完整的。
- GM-0101/0103：保证这条 T2 流程在 **玩法逻辑** 上是有意义、可测的。

## 3. 补齐 GM/NG 任务字段，让任务真正“可驱动”

针对 `NG-0021` 与 `GM-0103`（也可以适度补充 `GM-0101`），建议检查并补齐以下字段（示例）：

- `owner`：例如 `"owner": "you"`。
- `labels`：
  - 如 `"labels": ["t2-playable", "gm-core-loop", "godot-csharp"]`。
- `layer`：
  - NG-0020/0021：`"crosscutting"` 或类似。
  - GM-0101/0103：`"core"`。
- `adr_refs`：至少包含：
  - `ADR-0018`（Godot+C# 技术栈）、`ADR-0019`（安全基线）、`ADR-0003`（可观测性）、
    `ADR-0004`（事件总线）、`ADR-0005`（质量门禁）、`ADR-0025`（测试策略）等。
- `chapter_refs`：
  - 例如 `CH01`（目标）、`CH04`（系统上下文）、`CH06`（运行时视图）、`CH07`（开发与门禁）。
- `overlay_refs`：
  - `docs/architecture/overlays/PRD-Guild-Manager/08/08-功能纵切-公会管理器.md`。
  - `docs/architecture/overlays/PRD-Guild-Manager/08/ACCEPTANCE_CHECKLIST.md`。
- `test_refs`：
  - Core 测试（xUnit）：
    - `Game.Core.Tests/Domain/EventEngineTests.cs`。
    - `Game.Core.Tests/Domain/GameTurnSystemTests.cs`。
  - 场景测试（GdUnit4，占位或未来实现）：
    - `Tests.Godot/tests/Scenes/Guild/T2PlayableSceneTests.gd`。
- `acceptance`：
  - 包含文档一致性（PRD/Overlay/Checklist 对齐）与行为闭环（Week/Phase 正确变化）。

补齐后，运行：

```bash
py -3 scripts/python/task_links_validate.py
```

确认任务与 ADR / Overlay / 测试路径的回链均通过。

## 4. 先准备测试与场景骨架，而不是直接写逻辑

你希望核心“业务实现”交给 Taskmaster + SuperClaude，因此这一步只做“入口与骨架准备”：

### 4.1 Core 单元测试入口

- `Game.Core.Tests/Domain/GameTurnSystemTests.cs`：
  - 覆盖：
    - `StartNewWeek` 初始化 Week=1、Phase=Resolution、SaveId 等。
    - `Advance` 从 Resolution → Player → AiSimulation → 下一周 Resolution 的切换。
    - 可以扩展一个测试，验证“一轮 T2 流程结束后 Week>=2 且 Phase 回到 Resolution”。
- `Game.Core.Tests/Domain/EventEngineTests.cs`：
  - 维持现有的“三阶段不意外改动 Week/Phase”测试；
  - 预留一个 `[Fact]` 占位，描述未来实现 T2 行为时预期的事件发布/状态变更（可先作为 TODO）。

### 4.2 GdUnit4 场景测试骨架

- 在 `Tests.Godot/tests/Scenes/Guild/` 下预留：
  - `T2PlayableSceneTests.gd`（名称可按实际习惯调整）：
    - 说明：
      - 启动一个 T2 专用场景（如 GuildManagerT2 主场景）。
      - 模拟最小交互（点击“开始/结束本周”等）。
      - 断言 UI 上 Week/Phase 的变化（例如从 Week 1 → Week 2 且 Phase 重置为 Resolution）。

### 4.3 Godot 场景骨架

- 在 `Game.Godot/Scenes/` 中选定或创建 T2 入口场景：
  - 如 `Game.Godot/Scenes/Guild/GuildManagerT2.tscn`：
    - 初始版本只需基本布局（Label 显示 Week/Phase + 一个按钮）。
    - 逻辑先留给后续任务与 SuperClaude 来实现和绑定。

## 5. 用 GM/NG 任务驱动 SuperClaude 的开发节奏

在上述骨架准备完毕后，每一轮实际开发可以按以下节奏运行：

1. **任务选择与状态更新**
   - 从 `.taskmaster/tasks/tasks_back.json` / `tasks_gameplay.json` 中选择：
     - 优先完成 NG-0001 → NG-0020 → NG-0012 → NG-0021 这一条“基建 + CI”链路；
     - 然后聚焦 GM-0101 / GM-0103（回合循环与场景行为）。
   - 将任务状态从 `pending` 调整为 `in_progress`，记录 `owner`。

2. **前置校验（不改逻辑）**
   - 本地运行：
     ```bash
     py -3 scripts/python/task_links_validate.py
     ```
   - 确认任务、ADR、Overlay、测试引用链接无误。

3. **TDD 驱动的实现（交给 SuperClaude 完成）**
   - 在 Claude / SuperClaude 中提供：
     - 当前 GM/NG 任务的 JSON 段落；
     - `Game.Core.Tests/Domain/*.cs` 与 `Game.Core/Engine/*.cs` 相关文件；
     - PRD 与 Overlay 中关于 T2 场景流的段落。
   - 要求 SuperClaude 遵循：
     - 先补/改测试，再实现 Core 逻辑（EventEngine / GameTurnSystem）；
     - 暂不直接大幅修改 Godot 场景逻辑，只保证可以通过 T2 测试入口。

4. **回写 Taskmaster：acceptance 与 test_refs 对齐**
   - 当某一小步（例如完成一轮 Week 切换 + 测试通过）完成后：
     - 在对应 GM/NG 任务中更新：
       - `acceptance`：描述这一轮具体达成了什么（如“Week 可以从 1 切到 2，并回到 Resolution”）。
       - `test_refs`：确保引用的是实际存在且通过的测试文件。
     - 再次运行 `py -3 scripts/python/task_links_validate.py` 确认回链仍然干净。

## 6. “首个 T2 Playable 场景流”示例验收条款

可将以下内容（调整措辞后）同时写入：

- `GM-0103` 的 `acceptance` 数组；
- `ACCEPTANCE_CHECKLIST.md` 中对 T2 场景的条目。

> **首个 T2 Playable 场景流（GM‑0103 对齐）**
> - 启动游戏时，自动进入 Guild Manager T2 主场景或通过明显按钮一跳进入；
> - 场景中至少展示当前 Week 和 Phase（Resolution / Player / AiSimulation 三阶段之一）；
> - 玩家能够通过最少的点击完成一轮回合切换（例如点击“结束本周”按钮）；
> - 完成一轮后，Week 数字从 1 变为 2，Phase 重置为 Resolution，且 UI 有可观察到的变化（例如提示“Week 2 开始”）；
> - 整个流程中无未捕获异常，GdUnit4 场景测试在 CI 中 headless 通过；
> - 对应 GameTurnSystem / EventEngine 的行为由 xUnit 测试验证，且满足 ADR‑0015 中对回合循环性能的软门禁要求。

## 7. 心理模型小结

- PRD / Overlay / Checklist：定义“玩家要怎么从 0 到 1 玩一局”。
- NG‑0001/0020/0012/0021：保证这条 T2 流在文档/架构/测试/CI 层串通。
- GM‑0101/0103：保证这条 T2 流在玩法逻辑层成立。
- Game.Core.Tests：提供可编程的状态/事件验证入口。
- Tests.Godot：提供“可玩性闭环”的场景自动化验证。
- Godot 场景：是玩家实际看见和操作的 UI/交互入口。

按照本文档的顺序推进，你可以在不一次性铺开所有 GM/NG 任务的情况下，先落地一条“首个 T2 Playable 场景流”，并让后续的 Taskmaster + SuperClaude 流程围绕这条流逐步扩展游戏玩法。
