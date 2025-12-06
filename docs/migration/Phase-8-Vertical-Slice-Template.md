# Phase 8 纵向切片模板（Godot+C# + tasks.json）

> 目的：为 BMAD / task-master-ai / SuperClaude 提供一条标准的 Godot 纵向切片 Story 模板，示范如何从 PRD → ADR/Phase → tasks.json → 代码/测试，贯穿 Core/Adapters/Scenes/Tests 四层。

本文件不实现真实功能代码，仅定义“切片形状”和任务结构，供 AI 工具生成/校验使用。

---

## 1. 示例 Story：PH8-SCORE-VERTICAL-SLICE

- Story 名称：`PH8-SCORE-VERTICAL-SLICE`
- 目标：
  - 提供一个最小的“计分系统”竖切：
    - Core：新增 Score 服务/状态及 DomainEvent；
    - Adapter：通过 EventBusAdapter 将事件桥接到 Godot；
    - Scene/Glue：在 Main/HUD 中订阅 `core.score.updated` 并更新 UI；
    - Tests：xUnit + GdUnit4 覆盖 Score 服务与 HUD 更新路径。
- 关联文档/ADR：
  - ADR-0004-event-bus-and-contracts（事件总线与契约）
  - ADR-0006-data-storage（如计分需要持久化时）
  - ADR-0023-settings-ssot-configfile（如计分相关的显示设置）
  - CH05/CH06（数据模型与运行时视图）
  - Phase-8-Scene-Design（Main 场景布局与 Screen/HUD/Overlays）

该 Story 只是“形状示例”，真实项目可替换为任何领域切片，但建议保持同样的 Core→Adapter→Scene→Test 分解模式。

---

## 2. 任务拆分示例（tasks.json 片段）

以下为 `PH8-SCORE-VERTICAL-SLICE` 分解后的任务片段示意，供 task-master-ai 生成 `tasks.json` 时参考：

```jsonc
[
  {
    "id": "PH8-SCORE-CORE-001",
    "story_id": "PH8-SCORE-VERTICAL-SLICE",
    "title": "Add Score domain model and service",
    "layer": "core",
    "adr_refs": ["ADR-0004", "ADR-0006"],
    "chapter_refs": ["CH05", "CH06"],
    "overlay_refs": [],
    "description": "Introduce Score value object/service in Game.Core, including methods to add points and emit core.score.updated events via IEventBus.",
    "depends_on": []
  },
  {
    "id": "PH8-SCORE-ADAPTER-001",
    "story_id": "PH8-SCORE-VERTICAL-SLICE",
    "title": "Wire Score events to EventBusAdapter",
    "layer": "adapter",
    "adr_refs": ["ADR-0004"],
    "chapter_refs": ["CH06"],
    "overlay_refs": [],
    "description": "Ensure EventBusAdapter correctly forwards core.score.updated DomainEvents as DomainEventEmitted Signal to Godot scripts.",
    "depends_on": ["PH8-SCORE-CORE-001"]
  },
  {
    "id": "PH8-SCORE-SCENE-001",
    "story_id": "PH8-SCORE-VERTICAL-SLICE",
    "title": "Update HUD text on core.score.updated",
    "layer": "scene",
    "adr_refs": ["ADR-0004"],
    "chapter_refs": ["CH06", "Phase-8-Scene-Design"],
    "overlay_refs": [],
    "description": "In HUD.cs and Main.gd, subscribe to DomainEventEmitted and update HUD label when receiving core.score.updated.",
    "depends_on": ["PH8-SCORE-ADAPTER-001"]
  },
  {
    "id": "PH8-SCORE-TEST-CORE-001",
    "story_id": "PH8-SCORE-VERTICAL-SLICE",
    "title": "Add xUnit tests for Score service",
    "layer": "test",
    "adr_refs": ["ADR-0005"],
    "chapter_refs": ["CH07", "Phase-10-Unit-Tests"],
    "overlay_refs": [],
    "description": "Add Game.Core.Tests cases to validate Score service behaviour and that core.score.updated events are published via IEventBus.",
    "depends_on": ["PH8-SCORE-CORE-001"]
  },
  {
    "id": "PH8-SCORE-TEST-SCENE-001",
    "story_id": "PH8-SCORE-VERTICAL-SLICE",
    "title": "Add GdUnit4 HUD scene test for score updates",
    "layer": "test",
    "adr_refs": ["ADR-0005"],
    "chapter_refs": ["Phase-11-Scene-Integration-Tests-REVISED"],
    "overlay_refs": [],
    "description": "Add Tests.Godot GdUnit suite to assert HUD label updates when DomainEventEmitted(core.score.updated) is emitted.",
    "depends_on": ["PH8-SCORE-SCENE-001"]
  }
]
```

> 约束要点：
> - 每个任务带有唯一 id 和 story_id，便于回溯到原始 Story；
> - 所有任务都必须引用至少 1 条 ADR 以及关联章节（CH/Phase）；
> - `layer` 决定任务修改的目录范围，避免 Core/Scene/Adapter 混杂。

---

## 3. 对 task-master-ai 的具体要求

当 task-master-ai 将 PRD 中类似的“计分竖切 Story”转为任务时，应：

1. 识别 Story 中的层次：
   - Core 逻辑（计分规则/事件）；
   - Adapter（EventBusAdapter/数据存储）；
   - Scene/Glue（HUD/Main/ScreenNavigator 等）；
   - Tests（xUnit + GdUnit4）。

2. 为每个层次生成对应任务，并按本文件示例附带：
   - `layer` / `adr_refs` / `chapter_refs` / `overlay_refs`；
   - `depends_on` 关系，用于在执行任务时按“Core → Adapter → Scene → Tests”的顺序推进。

3. 将生成的 `tasks.json` 放到仓库约定位置（例如 `docs/tasks/tasks.json`），供 SuperClaude/Claude Code 和 Codex CLI 按顺序执行。

---

## 4. 对执行代理（SuperClaude/Codex）的建议

- 读取 `tasks.json` 时：
  - 先按 Story 聚合，再按 depends_on 拓扑排序；
  - 对 `layer="core"` 的任务优先改 `Game.Core/**` 与 `Game.Core.Tests/**`，并通过 dotnet 测试验证；
  - 对 `layer="adapter"`/`"scene"` 的任务，在 `Game.Godot/**` 中新增/修改 C# 与 GDScript，并通过 GdUnit4 小集验证；
  - 对 `layer="test"` 的任务，补充 xUnit/GdUnit4 用例，使上述改动有适当覆盖率。

- 在每一批任务完成后：
  - 优先调用 `py -3 scripts/python/dev_cli.py run-ci-basic ...` 确认核心门禁；
  - 在需要时调用 `py -3 scripts/python/dev_cli.py run-quality-gates --gdunit-hard --smoke ...` 做更严格验证。

---

## 5. 注意事项

- 本文件仅定义“纵向切片 Story 与任务结构模板”，不要求模板仓库内预置具体 Score Demo 代码，避免对真实项目造成约束。
- 真实项目应基于此模板定义自己的 Story/Story ID，并在 PRD/ADR/Phase 文档中维持一致的命名与回链。

