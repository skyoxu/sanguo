# 工作流优化说明：任务语义门禁与测试证据链（从上次提交到现在）

本文档记录本仓库近期对“每任务交付工作流”的增量优化，目标是降低“done 不真实”的概率：让脚本不仅对编译/单测负责，也能对任务语义（acceptance/test_strategy）形成可核验的证据链，并在关键阶段 fail-fast。

## 变更文件清单（本次提交覆盖范围）

说明：以下为本次工作流优化实际涉及的新增/修改文件（按路径），用于迁移到其他同构项目时做对照。

### 任务数据与上下文（本仓库状态相关）

- `.taskmaster/tasks/tasks_back.json`（修改）：新增/更新部分任务的 `test_refs`、`acceptance Refs:` 等字段（具体以 diff 为准）。
- `.taskmaster/tasks/tasks_gameplay.json`（修改）：同上。
- `taskdoc/11.md`（修改）：用于 sc-analyze 的辅助上下文文档（Serena 导出的 symbols/refs；迁移到其他仓库时通常不需要带走）。

### 文档模板与自动注入（SSoT 口径）

- `docs/testing-framework.md`（修改）：补充测试根目录 SSoT、`Refs:`/`test_refs` 证据链规则、默认路径约定与命名口径。
- `docs/testing-framework.auto.test-org-naming-refs.zh.md`（新增）：用于自动注入 `docs/testing-framework.md` 的片段（SSoT）。
- `scripts/python/update_testing_framework_from_fragments.py`（新增）：将片段注入到 `docs/testing-framework.md` 的标记区块（UTF-8，确定性）。

### 确定性分析与门禁（无 LLM）

- `scripts/sc/analyze.py`（修改）：按任务 id 输出 `task_context.<id>.json/.md`（避免覆盖），并接入 `taskdoc/<id>.md`（若存在）。
- `scripts/python/validate_task_context_required_fields.py`（新增）：校验 task_context 必填字段（red/green/refactor 统一 fail-fast）。
- `scripts/python/validate_acceptance_refs.py`（新增）：校验 acceptance 条款是否包含 `Refs:`，并在 refactor 阶段验证文件存在且被纳入 `test_refs`。
- `scripts/python/validate_task_test_refs.py`（新增）：校验任务级 `test_refs`（含 `--require-non-empty` 硬门禁）。
- `scripts/python/update_task_test_refs_from_acceptance_refs.py`（新增）：把 acceptance `Refs:` 同步进 `test_refs`（确定性 bookkeeping）。
- `scripts/python/update_task_test_refs.py`（新增）：保守地维护任务 `test_refs`（仅自动发现 `Game.Core.Tests/Tasks/Task<id>*Tests.cs`，不做语义猜测）。
- `scripts/python/audit_task_triplet_delivery.py`（新增）：对 triplet 任务视图做“证据完整性审计”（非语义验证）。

### TDD 阶段门禁（脚本串联）

- `scripts/sc/build/tdd.py`（修改）：
  - red/green/refactor 阶段开始前强制 `sc-analyze` + task_context 必填字段校验；
  - refactor 阶段增加 `acceptance Refs` 与 `test_refs` 的硬门禁；
  - 测试命名门禁采用止损策略：只对当前任务 `test_refs` 指向的 `.cs` 测试执行 strict。
- `scripts/python/check_test_naming.py`（修改）：新增 `--style strict|legacy` 与 `--task-id`（仅检查该任务证据范围）。

### 验收脚本（确定性）

- `scripts/sc/acceptance_check.py`（修改）：增加/强化 `--require-task-test-refs` 等确定性门禁能力（结合 triplet 证据链）。
- `scripts/sc/_acceptance_steps.py`（修改）：验收步骤编排调整（与新增门禁脚本对齐）。

### LLM 辅助生成（可选，用于加速补齐测试）

说明：LLM 只用于生成候选测试内容；最终仍以确定性门禁与实际 `scripts/sc/test.py` 通过为准。

- `scripts/sc/llm_generate_red_test.py`（新增）：生成任务对齐的红灯骨架（生成前强制 `acceptance Refs` 语法门禁；prompt 注入测试模板摘录）。
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`（新增）：只为 acceptance `Refs:` 指向但不存在的测试文件生成内容（prompt 注入测试模板摘录；可选自动跑测试验证）。

## 背景：为什么会出现“done 不真实”

传统的红/绿/重构循环与 `dotnet test`/覆盖率门禁，只能证明：

- 能编译、能运行、测试通过；
- 覆盖率达到阈值；
- 部分确定性规则通过（命名/引用/契约等）。

但它们并不会自动对 `tasks_back.json` / `tasks_gameplay.json` 中的 `acceptance` 与 `test_strategy` 的逐条语义负责。结果是：任务可能“测试都绿了”，但仍遗漏了某些验收条款（尤其是 Godot/UI 行为类）。

## 目标：把“任务语义”变成可确定性门禁

本轮优化引入两个核心约束：

1. **任务上下文必须全量化（triplet SSoT）**  
   在红/绿/重构开始前，强制生成并验证 `task_context.<id>.json`，确保脚本拿到 `tasks.json + tasks_back.json + tasks_gameplay.json + taskdoc/<id>.md` 的合并信息。

2. **acceptance 必须映射到测试证据（Refs -> test_refs）**  
   要求每条 `acceptance` 明确给出 `Refs:`，并且在 refactor 阶段强制：
   - 引用文件存在；
   - 引用文件被纳入该任务的 `test_refs`（任务级证据清单）。

## 关键改动与原因（按执行链路）

### 1) 生成“任务上下文”并强制必填字段（fail-fast）

- 在每个 `tdd --stage red|green|refactor` 开始前，自动执行一次任务分析，生成当日的任务上下文文件：
  - `logs/ci/<YYYY-MM-DD>/sc-analyze/task_context.<id>.json`
  - `logs/ci/<YYYY-MM-DD>/sc-analyze/task_context.<id>.md`
- 并在进入阶段前执行必填字段校验（硬失败）：
  - `scripts/python/validate_task_context_required_fields.py`

目的：避免“脚本只拿到 master 信息”而漏掉 back/gameplay 的 `acceptance/test_strategy/test_refs` 等关键字段。

### 2) acceptance 的 `Refs:` 规则 + refactor 阶段硬门禁

新增确定性校验脚本：

- `scripts/python/validate_acceptance_refs.py`

约束分阶段：

- `stage=red|green`：要求每条 acceptance 都必须有 `Refs:`（语法级），但不要求文件存在；
- `stage=refactor`：要求引用文件存在，并且必须包含在 `test_refs` 里（证据链闭环）。

目的：把“验收条款”变成可追踪的证据，避免验收停留在口头或主观判断。

### 3) `test_refs` 作为任务级证据清单（refactor 硬门禁）

新增确定性校验脚本：

- `scripts/python/validate_task_test_refs.py --require-non-empty`

并在 `tdd --stage refactor` 中启用硬门禁：要求 `tasks_back.json` 与 `tasks_gameplay.json` 的映射任务都具备非空 `test_refs`。

同时提供确定性的同步脚本：

- `scripts/python/update_task_test_refs_from_acceptance_refs.py --task-id <id> --write`

目的：避免只在 acceptance 写了 `Refs:`，但任务级 `test_refs` 没同步，导致后续任务无法复用/发现证据。

### 4) LLM 辅助生成测试：把模板与门禁一起注入

新增/更新 LLM 辅助脚本（均会写入 `logs/ci/<date>/` 以便取证）：

- `scripts/sc/llm_generate_red_test.py`  
  - 在生成红灯骨架前，会先跑 `validate_acceptance_refs --stage red`，没有 `Refs:` 直接硬失败；
  - prompt 会注入 `docs/testing-framework.md` 的“自动片段区块”（测试目录/命名/Refs 约定），减少跑偏。

- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`  
  - 只生成 acceptance `Refs:` 明确指向但尚不存在的测试文件；
  - 可选调用 `scripts/sc/test.py` 做 unit/all 验证；
  - 同样注入 `docs/testing-framework.md` 的自动片段区块。

目的：让“生成的测试文件”尽可能在一开始就贴合仓库规范，而不是事后纠偏。

### 5) 测试命名门禁：采用止损策略（任务证据 strict，全仓 legacy）

问题：如果把全仓命名直接收紧为 strict，会导致大量既有测试不合规，属于高风险破坏性改动。

决策：采用 A 策略：

- **全仓默认 legacy 放行**（便于渐进迁移）；
- **当前任务证据范围 strict**：仅对该任务 `test_refs` 指向的 C# 测试文件执行 strict 命名规则。

实现方式：

- `scripts/python/check_test_naming.py` 新增参数：
  - `--style legacy|strict`
  - `--task-id <id>`（仅检查该任务 `test_refs` 的 `.cs`）
- `tdd --stage refactor` 默认对当前任务执行：
  - `py -3 scripts/python/check_test_naming.py --task-id <id> --style strict`

目的：避免“治理性改动拖垮交付”，同时确保每个任务的证据文件是高质量、可复用、命名一致的。

## 文档模板与自动注入（UTF-8）

为避免手工编辑漂移，本轮引入自动片段机制：

- 片段源：`docs/testing-framework.auto.test-org-naming-refs.zh.md`
- 注入脚本：`scripts/python/update_testing_framework_from_fragments.py`
- 目标文档：`docs/testing-framework.md`（标记区块 `BEGIN/END AUTO:TEST_ORG_NAMING_REFS`）

目的：把“可执行规范”固定下来，并让脚本生成器与验收门禁引用同一份口径。

## 你现在应该怎么用（PowerShell）

### 每完成一个任务（推荐顺序）

1) 先跑确定性验收（不依赖 LLM）：

```powershell
py -3 scripts/sc/acceptance_check.py --task-id <id> --only adr,links,overlay,contracts,arch,security
```

2) 完整确定性门禁（需要 Godot bin 时再加参数）：

```powershell
$env:GODOT_BIN="C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"
py -3 scripts/sc/acceptance_check.py --task-id <id> --godot-bin "$env:GODOT_BIN" --perf-p95-ms 20
```

3) 进入 TDD 阶段（会自动跑 analyze 并校验 task_context 必填字段）：

```powershell
py -3 scripts/sc/build.py tdd --stage red --task-id <id>
py -3 scripts/sc/build.py tdd --stage green --task-id <id>
py -3 scripts/sc/build.py tdd --stage refactor --task-id <id>
```

### 命名门禁的止损策略

只检查任务证据范围（严格）：

```powershell
py -3 scripts/python/check_test_naming.py --task-id <id> --style strict
```

全仓仅观察（legacy）：

```powershell
py -3 scripts/python/check_test_naming.py --style legacy
```

## 注意事项

- `tdd --stage green/refactor` 不会自动生成新的测试源文件；只有 `--generate-red-test` 会生成 `Task<id>RedTests.cs` 临时骨架，且 refactor 阶段不允许保留该文件。
- `Refs:` 使用仓库根目录相对路径（例如 `Tests.Godot/tests/...`）；GdUnit4 运行器的 `--add tests/...` 属于 `--project Tests.Godot` 的项目内相对路径，两者不要混用。
- 旧任务如果 acceptance 未加 `Refs:`，会被新门禁拦截；应先补齐 `Refs:` 并同步到 `test_refs`，再进入 refactor 阶段。
