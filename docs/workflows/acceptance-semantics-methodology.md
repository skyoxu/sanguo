# Acceptance 贫血治理方法论（SSoT）

> 目标：把“done”从主观判断，收敛为**可审计、可复核、可自动化证据链**，并避免 acceptance 被无关条款稀释导致“语义验收缺失”。

本仓库以 `.taskmaster/tasks/tasks_back.json` 与 `.taskmaster/tasks/tasks_gameplay.json` 的任务视图为语义验收口径来源（允许缺一侧但至少存在一侧）。其中：

- `acceptance[]`：**任务语义验收条款**（必须可被测试证据证明）。
- `test_refs[]`：**任务证据清单**（验收条款与测试文件的聚合索引）。
- `test_strategy[] / details`：**实施策略与过程信息**（不作为硬验收口径）。

## 1. 为什么会出现“done 不真实”

常见根因不是代码没写，而是“语义没有固化为可验证条款”：

- `acceptance[]` 只剩“Core 不依赖 Godot”这种**跨任务通用约束**，没有任务独有行为/不变式。
- `acceptance[]` 混入本地 demo 路径、学习资料、CI 事实、操作步骤，导致真正的验收条款被挤掉。
- `Refs:` 指向不存在文件，或 `test_refs[]` 不包含全部 `Refs:`，导致证据链断裂。
- `ACC:T<id>.<n>` anchor 只是“文件出现过”，但没有绑定到具体测试方法，形成“可通过但不可审计”的假阳性。

## 2. acceptance 的最小语义集（建议）

每个任务的 `acceptance[]` 至少应包含以下 3 类中的 2 类（越靠前越推荐）：

1) **行为（Behavior）**：输入/条件 → 产出/副作用（含事件/状态变化）

- 例：购买城池成功会扣钱、获得所有权、发布 `SanguoCityBought`。

2) **不变式（Invariant）**：始终成立的约束（唯一写入口、范围约束、幂等等）

- 例：城市价格倍率必须在 `[0, MaxPriceMultiplier]`，否则抛异常。

3) **失败语义（Failure Semantics）**：失败时系统如何表现（抛异常/返回 false/回滚/不中断循环）

- 例：事件 handler 抛异常不影响其他 handler；Publish 失败是否回滚并抛出。

说明：

- “Core 不依赖 Godot API”属于通用约束，只在该任务确实新增/引入 Core 类型时才放入 acceptance；否则应放到 `test_strategy[]` 或由全局质量门禁覆盖。
- UI/场景类任务应把“可见性/信号/事件驱动 UI 更新”等写成 acceptance，并通过 GdUnit4/headless 产证据。

## 2.5 ?????Obligations?? ????no-op ???

??? acceptance ????????????????**????**???? subtasks ??????????????

- ?????????????????????????? AdvanceTurn ????????????????
- acceptance ?????????????????/??????????????

?????? *LLM ??*??????????? pending/in-progress ????

- ???`py -3 scripts/sc/llm_extract_task_obligations.py --task-id <id>`
- ?????????
  - `tasks.json` ? `master.details` / `master.testStrategy`
  - `tasks.json` ? `subtasks[].title/details/testStrategy`?????
  - `tasks_back/tasks_gameplay` ? `acceptance[]`
- ???`logs/ci/<YYYY-MM-DD>/sc-llm-obligations-task-<id>/verdict.json` + `report.md`

?????????

- ?? obligation ?? **???/???**????????/??????????????
- ?? obligation ??? `source_excerpt`?? **???????????**??? LLM ??????
- ???? uncovered obligation????? `fail`?????????? acceptance ????????? `Refs:`??

??????? Step1 ???????????????????

- ? pending/in-progress ??? `llm_align_acceptance_semantics.py --structural-for-not-done` ?????append-only???
- ? done ??? `llm_align_acceptance_semantics.py --append-only-for-done` ????????????? `ACC:T<id>.<n>` anchors??

## 3. 禁止项：哪些内容不应留在 acceptance

下列条款应迁移到 `test_strategy[]` 或 `details`：

- `Local demo references:` 或任何外部绝对路径（例如 `C:\...`）。
- 学习资料、参考项目、实施步骤、命令行说明。
- CI 事实类条款（例如“覆盖率达标”“测试存在并通过”）。
- “可能/建议/可选”类条款（除非明确转为硬验收并提供测试证据）。

## 4. Refs 与 anchors：把条款绑定到证据

本仓库约束以 `docs/testing-framework.md` 为准，核心原则如下：

- `acceptance[]` 的**每条**必须以 `Refs: <repo-relative-test-path>[, ...]` 结尾。
- `test_refs[]` 必须至少包含该任务所有 acceptance `Refs:` 的并集。
- `ACC:T<id>.<n>` 作为语义绑定 anchor：第 `n` 条 acceptance 的 `Refs:` 指向测试文件中，必须出现 `ACC:T<id>.<n>`。
- anchors 建议作为注释贴近具体测试方法（xUnit `[Fact]` 或 GdUnit4 `func test_...`），避免“文件出现过但不可归因”。

## 5. 迁移优先、补齐为辅：治理流程（可重复）

1) **清洗**：把非确定性/过程条款从 `acceptance[]` 迁移到 `test_strategy[] / details`。
2) **补齐**：为每个任务写 2–6 条“可被测试证明”的 acceptance（行为/不变式/失败语义）。
3) **绑定**：每条 acceptance 填 `Refs:`，并在对应测试方法附近补 `ACC:T<id>.<n>`。
4) **汇总**：更新 `test_refs[]`（替换模式优先，避免历史漂移）。
5) **验收**：在 `refactor` 阶段启用硬门禁（Refs 文件存在、Refs ⊆ test_refs、anchors 绑定通过）。

## 6. 产物与取证

所有自动化输出统一落 `logs/ci/<YYYY-MM-DD>/`（详见 `AGENTS.md` 的 6.3），用于：

- 复盘 “为何 fail-fast”
- 对比治理前后差异
- 作为 PR 证据链的一部分

