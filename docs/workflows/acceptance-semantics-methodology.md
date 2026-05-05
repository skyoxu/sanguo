# Acceptance 贫血治理方法论（SSoT）

> 目标：把“done”从主观判断，收敛为可审计、可复核、可自动化的证据链，并避免 acceptance 被无关条款稀释导致“语义验收缺失”。

本仓库采用“任务三元组（triplet）”口径：

- `.taskmaster/tasks/tasks.json`：主任务（SSoT：任务是否完成、子任务拆分、实现过程摘要）
- `.taskmaster/tasks/tasks_back.json` / `.taskmaster/tasks/tasks_gameplay.json`：视图任务（SSoT：验收语义、测试证据、ADR/CH/Overlay 回链）
- 视图缺省：允许某个任务只存在于 `tasks_back.json` 或只存在于 `tasks_gameplay.json`；另一侧视图视为 `warning/skip`，但至少要存在一侧。

视图任务中关键字段口径（以 snake_case 为准）：

- `acceptance[]`：任务语义验收条款（必须可被测试证据证明）
- `test_refs[]`：证据清单（验收条款与测试文件的聚合索引）
- `test_strategy[]`：实施策略与过程信息（不作为硬验收口径）
- `adr_refs[] / chapter_refs[] / overlay_refs[]`：审计链路锚点（引用必须存在且可追溯）

## 1. 为什么会出现“done 不真实”

常见根因不是代码没写，而是“语义没有固化为可验证条款”：

- `acceptance[]` 只剩“跨任务通用约束”，缺少该任务独有的行为/不变式/失败语义
- `acceptance[]` 混入本地 demo 路径、学习资料、命令行说明、CI 事实，导致真正验收条款被挤掉
- `Refs:` 指向不存在文件，或 `test_refs[]` 未覆盖 acceptance 的全部 `Refs:`，导致证据链断裂
- `ACC:T<id>.<n>` 只是“文件里出现过”，但未绑定到具体测试方法，形成“可通过但不可审计”的假阳性

## 2. acceptance 的最小语义集（建议）

每个任务的 `acceptance[]` 至少应覆盖下列 3 类中的 2 类（越靠前越推荐）：

1) **行为（Behavior）**：输入/条件 → 输出/副作用（含事件、状态变化）

- 例：创建示例模块成功会发布 `ExampleCreated`，并把 `EntityId/CreatorId/CreatedAt` 写入状态。

2) **不变式（Invariant）**：始终成立的约束（范围/白名单/单写入口/资源边界）

- 例：任何文件写入只能发生在 `user://`，且拒绝包含 `..` 的路径。

3) **失败语义（Failure Semantics）**：失败时系统如何表现（抛异常/返回 false/回滚/不中断循环）

- 例：某个事件 handler 抛异常不会影响其他 handler；失败会记录审计条目但不会泄露敏感路径。

说明：

- “Core 不依赖 Godot API”属于通用约束，只有当该任务确实新增/修改 Core 类型时才放进 acceptance；否则放入 `test_strategy[]`，由全局门禁覆盖。
- UI/场景类任务应把“可见性/信号/事件驱动 UI 更新”等写成 acceptance，并通过 GdUnit4/headless 产出证据。

## 2.5 “Obligations”补全（可选，LLM 软辅助）

当任务处于 `pending/in-progress`，且 acceptance 明显偏“过程描述”或“通用口号”时，可以抽取 obligations 做一次对齐：

- 抽取范围：`tasks.json` 的 `details/testStrategy`、`subtasks[].title/details/testStrategy`，以及视图任务的 `acceptance[]`
- 产物要求：输出必须包含 `source_excerpt`（原文片段）以便人工复核，避免 LLM 误读
- 建议命令（如仓库已有对应脚本）：`py -3 scripts/sc/llm_extract_task_obligations.py --task-id <id>`
- 取证落盘：`logs/ci/<YYYY-MM-DD>/sc-llm-obligations-task-<id>/verdict.json` 与 `report.md`

若 obligations 与 acceptance 存在缺口，应先补 acceptance，再进入 red/green/refactor。

## 3. 禁止项：哪些内容不应留在 acceptance

下列条款应迁移到 `test_strategy[]` 或 `details`：

- 本地 demo references 或任何外部绝对路径（例如 `C:\...`）
- 学习资料、参考项目、实施步骤、命令行说明
- 纯 CI 事实条款（例如“覆盖率达标”“测试存在并通过”）
- “可能/建议/可选/加固”类条款（除非明确转为硬验收并提供测试证据）

## 4. Refs 与 anchors：把条款绑定到证据

以 `docs/testing-framework.md` 为准，核心原则：

- 每条 `acceptance[]` 必须以 `Refs: <repo-relative-test-path>[, ...]` 结尾
- `test_refs[]` 必须至少包含该任务所有 acceptance `Refs:` 的并集
- `ACC:T<id>.<n>` 作为语义绑定 anchor：第 `n` 条 acceptance 对应的测试文件中必须出现 `ACC:T<id>.<n>`
- anchor 建议贴近具体测试方法（xUnit `[Fact]` 或 GdUnit4 `func test_...`），避免“出现过但不可归因”

## 5. 治理流程（可重复）

1) **清洗**：把不确定性/过程条款从 `acceptance[]` 迁移到 `test_strategy[] / details`
2) **补齐**：为每个任务补 2–5 条“可被测试证明”的 acceptance（行为/不变式/失败语义）
3) **绑定**：每条 acceptance 填 `Refs:`，并在对应测试方法附近补 `ACC:T<id>.<n>`
4) **汇总**：同步/更新 `test_refs[]`（以“覆盖 acceptance Refs 为主”，避免历史漂移）
5) **验收**：在门禁阶段启用硬校验（Refs 文件存在、Refs ⊆ test_refs、anchors 绑定通过）

## 6. 产物与取证

所有自动化输出统一落盘到 `logs/ci/<YYYY-MM-DD>/`（目录口径见 `AGENTS.md`），用于：

- 复盘为何 fail-fast
- 对比治理前后差异
- 作为 PR 证据链的一部分

## 7. Parameter baseline (2026-02 alignment)

- `llm_extract_task_obligations.py`: `--task-id <id> --consensus-runs 3 --garbled-gate on --auto-escalate on`
- `llm_check_subtasks_coverage.py`: `--task-id <id> --consensus-runs 3`
- `llm_semantic_gate_all.py`: `--task-ids <csv> --consensus-runs 3 --garbled-gate on`
- Security-sensitive tasks should pass explicit `--security-profile host-safe|strict` and use `acceptance_check.py` as final authority.
