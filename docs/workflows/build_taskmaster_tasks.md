1. 新脚本：`scripts/python/build_taskmaster_tasks.py`

- 功能（基于 Task Master MCP 约束）：
  - 从指定的任务文件中读取 NG/GM 任务（默认是 `.taskmaster/tasks/tasks_back.json`、`tasks_gameplay.json`、`tasks_longterm.json`，由调用方通过 `--tasks-file` 显式指定）。
  - 以给定的任务 ID 集合作为“根任务”，根据 `depends_on` 计算依赖闭包；如未显式指定 ID，则使用内置的 T2 根集合（`NG-0020`、`NG-0021`、`GM-0101`、`GM-0103`）。
  - 将闭包中的任务转换为 Task Master 兼容的 `.taskmaster/tasks/tasks.json` 结构，在指定 Tag（默认 `master`）下以 **数字 ID + 数字依赖** 的形式保存。
  - 为源任务文件中的对应任务追加标记字段：
    - `taskmaster_id`: 映射后的数字 ID；
    - `taskmaster_exported`: 是否至少被一次导出到 `tasks.json`（布尔值）。

- 关键点（符合 `docs/task-master-constraints.md`）：
  - 根对象结构：`{ "<tag>": { "tasks": [...] }, ... }`（多 Tag 并存）。
  - 每个 Task Master 任务：
    - `id: number`（全局唯一，跨 Tag 不冲突）
    - `title: string`
    - `description: string`
    - `status: "pending" | "in-progress" | "done" | "deferred" | "cancelled" | "blocked"`（由现有状态映射而来）
    - `priority: "high" | "medium" | "low"`（由 P1/P2/P3 映射而来）
    - `dependencies: number[]`（由字符串 `depends_on` 映射）
    - `testStrategy: string`（从 `test_strategy[]` 合并为多行文本）
    - `details: string`（将 `story_id` / `adr_refs` / `chapter_refs` / `overlay_refs` / `test_refs` / `acceptance` / `test_strategy` / `labels` / `owner` / `layer` 等聚合为 markdown 风格说明）

---

2. 参数与用法（可复用、可叠加）

`scripts/python/build_taskmaster_tasks.py` 现在支持：

- `--tag`：写入/更新的 Task Master Tag 名，默认 `"master"`。
- `--tasks-file`：源任务文件路径，可多次指定，例如：
  - `.taskmaster/tasks/tasks_back.json`
  - `.taskmaster/tasks/tasks_gameplay.json`
  - `.taskmaster/tasks/tasks_longterm.json`
  > 这是**必填参数**；如果未指定 `--tasks-file`，脚本会直接报错退出（不再隐式使用默认文件集）。
- `--ids`：要导出的任务 ID 字符串数组（如 `NG-0001 NG-0020 GM-0101`），脚本会以这些 ID 为根，包含其依赖闭包。
- `--ids-file`：一个 JSON 文件，内部是字符串 ID 数组，例如：`["NG-0001","NG-0020","GM-0101"]`，用于避免命令行上敲很长的 ID 列表。
  - 若同时提供 `--ids` 与 `--ids-file`，两者取并集作为根集合。
  - 如两者都未提供，则退回使用内置 T2 根集合（`T2_ROOT_IDS`）。

示例调用：

```bash
# 默认 T2 用法：从三份任务文件加载任务，以内置 T2 根任务为起点，计算依赖闭包并写入 master Tag
py -3 scripts/python/build_taskmaster_tasks.py \
  --tasks-file .taskmaster/tasks/tasks_back.json \
  --tasks-file .taskmaster/tasks/tasks_gameplay.json \
  --tasks-file .taskmaster/tasks/tasks_longterm.json \
  --tag master

# 自定义：从 tasks_back.json 中选 NG-0001 和 NG-0013 的闭包，写入 feature-docs Tag
py -3 scripts/python/build_taskmaster_tasks.py \
  --tasks-file .taskmaster/tasks/tasks_back.json \
  --ids NG-0001 NG-0013 \
  --tag feature-docs

# 使用 JSON 提供 ID 列表（例如 .taskmaster/tasks/t2_ids.json 中是 ["NG-0001","NG-0020","GM-0101"]）
py -3 scripts/python/build_taskmaster_tasks.py \
  --tasks-file .taskmaster/tasks/tasks_back.json \
  --tasks-file .taskmaster/tasks/tasks_gameplay.json \
  --ids-file .taskmaster/tasks/t2_ids.json \
  --tag master
```

---

3. 自动追加到 `tasks.json`（不覆盖已有 Tag）

脚本当前的 Task Master 输出逻辑：

1. 如果 `.taskmaster/tasks/tasks.json` 已经存在：
   - 先读取现有内容；
   - 保留所有已有 Tag（例如 `"master"`、`"ng-backbone"`、`"gm-gameplay"` 等），**只对指定的 `--tag` 做增量更新**。
2. 针对指定的 `--tag`（默认 `"master"`）：
   - 确保存在 `root_obj[tag].tasks` 列表；
   - 收集所有 Tag 中已经使用过的数字 ID，避免冲突；
   - 遍历本次闭包中的任务字符串 ID（例如 `NG-0001`、`NG-0020` 等），为每个分配数字 ID：
     - 优先复用源任务中已有的 `taskmaster_id`（若存在且未与已用 ID 冲突）；
     - 否则分配一个新的全局唯一数字 ID（递增，不与任何 Tag 中已用 ID 冲突）。
   - 构建 Task Master 任务对象：
     - `id`（数字）
     - `title`、`description`
     - `status`（标准枚举）
     - `priority`（标准枚举）
     - `dependencies`（将 `depends_on` 字段中的字符串 ID 转成对应数字 ID）
     - `details`（聚合元信息）
     - `testStrategy`（从 `test_strategy` 数组合并而来）
3. 在目标 Tag 下：
   - 如果该数字 ID 已存在任务：**更新**该任务（覆盖 title/description/details/testStrategy 等内容）；
   - 如果不存在：追加新任务到列表末尾。

因此，多次运行脚本（不同 `--tag` 或 `--ids`）会在同一个 `tasks.json` 中**持续追加/更新**指定 Tag，而不会破坏其他 Tag 的内容。

---

4. 原始任务文件中的标记字段（taskmaster_id / taskmaster_exported）

脚本在每次运行后，会在 **本次通过 `--tasks-file` 指定的源任务文件** 中更新 bookkeeping 字段：

- 对于本次闭包中的任务：
  - 写入/更新：`taskmaster_id` 为对应数字 ID；
  - 写入/更新：`taskmaster_exported = true`。
- 对于同一个源文件中、但不在本次闭包里的任务：
  - 如果之前已经有 `taskmaster_exported: true`，保持不变（保留“曾经导出过”的事实）；
  - 如果没有该字段，则补一个 `taskmaster_exported: false`，表示“尚未被任何一次 build/export 选中”。

示例（在 `.taskmaster/tasks/tasks_back.json` 中）

```json
{
  "id": "NG-0020",
  "title": "...",
  "status": "pending",
  "...": "...",
  "taskmaster_id": 5,
  "taskmaster_exported": true
}

{
  "id": "NG-0013",
  "...": "...",
  "taskmaster_exported": false
}
```

这样：

- 你 / Serena 可以在 NG/GM SSoT 文件里快速识别哪些任务已经暴露给 Task Master MCP 使用（有 `taskmaster_id` 且 `taskmaster_exported=true`）；
- 扩展导出集合时，只需通过 `--tasks-file` / `--ids` / `--ids-file` 选择新的任务，再运行脚本即可自动更新映射；
- 不会出现“脚本偷偷修改其它未参与本次调用的任务文件”的情况——**只更新本次显式传入的 `--tasks-file` 列表**。