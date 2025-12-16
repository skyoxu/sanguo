# 任务驱动首个 T2 可玩闭环（sanguo）

> 说明：本文件名沿用历史命名（GM/NG），但 sanguo 项目不启用 Guild Manager；本文件已改为 sanguo 的 T2 可玩闭环工作流说明。

## 1. 先锁定单一事实来源（PRD + Overlay）

- PRD：`.taskmaster/docs/prd.txt`（T2「最小可玩闭环」描述）
- Overlay 索引：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- 验收清单：`docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`

## 2. 任务驱动（Taskmaster 三文件一致）

任务信息以三文件映射为准：

- `tasks.json.master.tasks[].id`
- `tasks_back[].taskmaster_id`
- `tasks_gameplay[].taskmaster_id`

建议在推进每个任务前先跑回链校验，避免“实现了但不可追溯/不可验收”：

- `py -3 scripts/python/task_links_validate.py`
- `py -3 scripts/python/validate_task_overlays.py`
- `py -3 scripts/python/validate_contracts.py`

## 3. TDD 落地节奏（最小闭环优先）

在不新建契约文件的前提下（Contracts 以 `Game.Core/Contracts/**` 为 SSoT）：

1. 红：补/改 xUnit 失败用例（优先领域不变式与关键计算）
2. 绿：最小实现让测试变绿
3. 重构：仅在不改变行为的前提下清理命名/重复/结构

## 4. 最小可玩闭环定义（可执行）

当以下内容都满足时，可以认为“掷骰→移动→轮到谁”的骨架已具备可展示价值：

- 领域层可计算：掷骰点数、环形移动、回合推进（日期/玩家轮转）
- 事件契约可用：`core.sanguo.*` 事件类型在 `Game.Core/Contracts/Sanguo/**` 中可引用且有单测护栏
- 质量门禁可跑：`dotnet build -warnaserror` 与 `dotnet test --collect:"XPlat Code Coverage"`（阈值口径见 ADR-0005）

