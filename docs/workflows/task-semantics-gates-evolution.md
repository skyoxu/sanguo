# 工作流说明：任务语义门禁与测试证据链（当前版本）

本文档记录本仓库近期对“每任务交付工作流”的增量优化，目标是降低“done 不真实”的概率：让脚本不仅对编译/单测负责，也能对任务语义（acceptance/test_strategy）形成可核验的证据链，并在关键阶段 fail-fast。

## 关键文件与脚本索引（截至当前版本）

说明：以下列出与本工作流直接相关的文件/脚本（按路径）；不保证穷尽，但应覆盖“结构/回链/语义/证据链/验收”的主干。

### 任务数据与上下文（仓库状态相关）

- `.taskmaster/tasks/tasks.json`：master 任务（含 subtasks）；部分脚本会从这里选择 `status=in-progress` 的任务作为默认对象。
- `.taskmaster/tasks/tasks_back.json`：NG 视图任务（架构/基础设施/跨切面为主），包含 `acceptance/test_strategy/test_refs/adr_refs/chapter_refs/overlay_refs/contract_refs` 等证据字段。
- `.taskmaster/tasks/tasks_gameplay.json`：GM 视图任务（玩法为主），字段口径同上。
- `taskdoc/<id>.md`（可选，本地上下文）：用于补充 `scripts/sc/analyze.py` 的输入（例如 Serena 导出的 symbols/refs）。建议保持 gitignored，仅作为本地取证/加速材料。

### 文档模板与自动注入（SSoT 口径）

- `docs/testing-framework.md`：测试组织与证据链口径（目录、命名、`Refs:`/`test_refs`、anchors 等）。
- `docs/testing-framework.auto.test-org-naming-refs.zh.md`：自动注入片段源（SSoT）。
- `scripts/python/update_testing_framework_from_fragments.py`：将片段注入到 `docs/testing-framework.md` 的标记区块（UTF-8，确定性）。

### 结构与回链（确定性，无 LLM）

- `scripts/python/validate_task_master_triplet.py`：三份任务文件一致性（映射、depends_on、无环）+ ADR/CH/Overlay 全量引用校验（内部调用 `check_tasks_all_refs.py`）。
- `scripts/python/verify_task_mapping.py`：人类可读 mapping 报告（不是 CI 硬门禁）。
- `scripts/python/task_links_validate.py`：回链“一键硬门禁”（内部调用 `check_tasks_back_references.py` + `check_tasks_all_refs.py`）。
- `scripts/python/validate_task_overlays.py`：overlay 引用与 `ACCEPTANCE_CHECKLIST.md` Front Matter 校验。

### 确定性分析与证据链（无 LLM）

- `scripts/sc/analyze.py`：生成任务上下文 `task_context.<id>.json/.md`（合并 master + back + gameplay + taskdoc）。
- `scripts/python/validate_task_context_required_fields.py`：校验 task_context 必填字段（fail-fast）。
- `scripts/python/validate_acceptance_refs.py`：校验 acceptance `Refs:`（red/green 语法；refactor 文件存在且纳入 `test_refs`）。
- `scripts/python/update_task_test_refs_from_acceptance_refs.py`：把 acceptance `Refs:` 同步进任务级 `test_refs`（replace/merge）。
- `scripts/python/validate_task_test_refs.py`：校验任务级 `test_refs`（可启用 `--require-non-empty`）。
- `scripts/python/update_task_test_refs.py`：保守维护 `test_refs`（仅自动发现 `Game.Core.Tests/Tasks/Task<id>*Tests.cs`，不做语义猜测）。
- `scripts/python/audit_task_triplet_delivery.py`：triplet 证据完整性审计（非语义验证）。
- `scripts/python/migrate_task_optional_hints_to_views.py`：把 demo/可选项/加固建议从 `tasks.json` 迁移到视图 `test_strategy`（确定性，避免污染 acceptance）。

### TDD 阶段门禁（脚本串联）

- `scripts/sc/build/tdd.py`：red/green/refactor gatekeeper（前置 analyze+必填字段；refactor 强制 Refs/test_refs 等硬门禁；任务证据范围 strict 命名）。
- `scripts/python/check_test_naming.py`：测试命名门禁（legacy/strict；可按 `--task-id` 限定证据范围）。

### 验收脚本（确定性）

- `scripts/sc/acceptance_check.py`：可复现确定性门禁（ADR/links/overlay/contracts/arch/security/tests/perf/risk 等）。
- `scripts/sc/_acceptance_steps.py`：验收步骤编排（内部依赖）。

### LLM 辅助（可选，用于语义/测试加速）

- `scripts/sc/llm_extract_task_obligations.py`：单任务义务抽取（obligations vs acceptance 覆盖诊断）。
- `scripts/sc/llm_align_acceptance_semantics.py`：批量对齐 acceptance 语义（acceptance-only phase）。
- `scripts/sc/llm_check_subtasks_coverage.py`：单任务 subtasks 覆盖检查。
- `scripts/sc/llm_semantic_gate_all.py`：批量语义 gate（ok/needs_fix/unknown）。
- `scripts/sc/llm_fill_acceptance_refs.py`：为 acceptance 自动补齐/改写 `Refs:`。
- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`：按 `Refs:` 生成缺失测试文件（可选跑 unit/all 验证）。
- `scripts/sc/llm_generate_red_test.py`：生成任务对齐的 red 测试文件（可选验证 red 阶段）。
- `scripts/sc/llm_review.py`：LLM 软审查（可注入 BMAD 模板；以 `sc-acceptance-check` 工件约束跑偏）。

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

补充口径（triplet 视图缺省）：

补充口径（治理口径原句）：

- 允许缺一侧但至少存在一侧（back 或 gameplay）视图条目存在；存在的那一侧继续严格要求（acceptance/test_strategy/test_refs/回链/门禁）。


- 允许任务只存在于 `tasks_back.json` 或只存在于 `tasks_gameplay.json`（另一侧视图 warning/skip），但至少必须存在一侧视图。
- 对“存在该任务条目”的那一侧视图，继续严格要求 `overlay_refs/test_strategy/acceptance/test_refs` 按阶段满足门禁。

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

- `scripts/python/update_task_test_refs_from_acceptance_refs.py --task-id <id> --mode replace --write`

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

本节给出“新生成 `.taskmaster/tasks/tasks.json` + 视图任务文件”的稳健顺序。

- 所有脚本读写都以 UTF-8 为准；在 Windows 控制台里建议统一用 `py -3` 执行脚本，避免 PowerShell/Console codepage 导致中文乱码或 JSON 解析失败。
- 你现在的治理链路是“两段式”：先把 `acceptance` 语义对齐，再补 `Refs:`/`test_refs` 并落地测试证据。

### 0) 结构与回链（确定性，无 LLM）

#### 0.1 硬结构先过：任务映射字段一致 + 至少一侧视图存在

- `scripts/python/validate_task_master_triplet.py`
  - 意义：验证三份任务文件一致性（视图↔master 映射、depends_on、无环），并串联 ADR/CH/Overlay 的全量引用校验（内部调用 `check_tasks_all_refs.py`）。
  - 建议用法：无参数，直接跑；非 0 退出码视为 fail-fast。

```powershell
py -3 scripts/python/validate_task_master_triplet.py
```

- `scripts/python/verify_task_mapping.py`
  - 意义：人类可读报告，逐个 master task 输出：back/gameplay 两侧是否存在映射条目、是否至少一侧具备核心元数据（adr_refs/test_refs/acceptance/story_id）。
  - 建议用法：无参数；这是“报告”，不是 CI 硬门禁。

```powershell
py -3 scripts/python/verify_task_mapping.py
```

说明：`validate_task_master_triplet.py` 当前对 `layer` 允许值为 `docs|core|adapter|ci`，因此会把 `ui/infra` 打印为 invalid（更像 warning）。如果你准备把 `layer` 变成硬门禁，需要先统一口径（例如把 UI 任务映射为 `adapter` 或扩展允许集合）。

#### 0.2 回链先对齐：ADR/CH/Overlay 引用校验

- `scripts/python/task_links_validate.py`
  - 意义：回链的“一键硬门禁”。它会执行：
    1) `scripts/python/check_tasks_back_references.py`：只检查 backlog-only（`taskmaster_exported != true`）条目；
    2) `scripts/python/check_tasks_all_refs.py`：全量检查 `tasks_back.json + tasks_gameplay.json` 的 `adr_refs/chapter_refs/overlay_refs`。
  - 建议用法：无参数；非 0 退出码视为 fail-fast。

```powershell
py -3 scripts/python/task_links_validate.py
```

- `scripts/python/validate_task_overlays.py`
  - 意义：校验 overlay 文件引用与 `ACCEPTANCE_CHECKLIST.md` 的 Front Matter（避免 overlay 结构漂移后 tasks 还指向旧路径）。
  - 建议用法：默认校验 `.taskmaster/tasks/*.json`；需要排障时可缩小到单文件。

```powershell
py -3 scripts/python/validate_task_overlays.py
py -3 scripts/python/validate_task_overlays.py --task-file .taskmaster/tasks/tasks_back.json
py -3 scripts/python/validate_task_overlays.py --task-file .taskmaster/tasks/tasks_gameplay.json
```

补充：通常不需要直接跑 `check_tasks_back_references.py/check_tasks_all_refs.py`；只有在你想单独定位某一类告警（例如“extra chapter_refs”）时，才建议直接运行它们。

### 1) 语义对齐（LLM，acceptance-only 阶段；Refs 先不补）

#### 1.1 可选提示迁移（deterministic）：把 demo/可选项/加固建议迁出 tasks.json

- `scripts/python/migrate_task_optional_hints_to_views.py`
  - 意义：把 `tasks.json` 里不应成为“验收义务”的句子迁移到视图文件的 `test_strategy/details`（并加 `Optional:` 前缀），避免以后语义门禁误把它们当成必须实现的 acceptance。
  - 建议用法：先 dry-run，再 `--write` 落盘；可用 `--task-ids` 只处理部分任务。
  - 注意：该脚本不处理 subtasks（只针对 master tasks）。

```powershell
py -3 scripts/python/migrate_task_optional_hints_to_views.py
py -3 scripts/python/migrate_task_optional_hints_to_views.py --task-ids 6,12,17 --write
```

#### 1.2 单任务“义务抽取”（可选，诊断用）：从 master.details+视图描述中抽取 obligations

- `scripts/sc/llm_extract_task_obligations.py`
  - 意义：对单个任务做“义务列表 vs acceptance 覆盖”分析，产出报告与 verdict，适合定位像 “T17.1 被漏掉” 这种问题。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-obligations-task-<id>/`（含 `summary.json`、`report.md`）。
  - 建议用法：务必显式传 `--task-id`（当 tasks.json 没有 in-progress 时，默认选择会失败）。

```powershell
py -3 scripts/sc/llm_extract_task_obligations.py --task-id 17
```

#### 1.3 批量对齐 acceptance（主流程）：让 acceptance 集合与任务描述语义尽量等价

- `scripts/sc/llm_align_acceptance_semantics.py`
  - 意义：对齐“任务描述 ↔ acceptance 集合”的语义（acceptance-only phase），按需把视图描述与 master 对齐，并把可选提示从 tasks.json 迁出（可选 preflight）。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-align-acceptance-semantics/summary.json`。
  - 建议用法：
    - 新任务/未完成任务：优先 `--scope not-done --apply --preflight-migrate-optional-hints`；
    - 已 done 任务：如果只是补少量“语义空洞”，优先 `--scope done --apply --append-only-for-done`（尽量不改动已有 anchors/Refs）。

```powershell
# 未完成任务：结构化对齐 + 允许脚本先迁移 optional hints
py -3 scripts/sc/llm_align_acceptance_semantics.py --scope not-done --apply --preflight-migrate-optional-hints

# 已完成任务：止损模式（只追加，不重写）
py -3 scripts/sc/llm_align_acceptance_semantics.py --scope done --apply --append-only-for-done
```

#### 1.4 子任务覆盖校验（仅对有 subtasks 的任务）

- `scripts/sc/llm_check_subtasks_coverage.py`
  - 意义：检查 subtasks 的 title+details 是否被当前 acceptance 覆盖；用于发现“主任务通过了，但子任务义务漏实现”的风险。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-subtasks-coverage-task-<id>/`（含 `summary.json`、`report.md`）。
  - 建议用法：务必显式传 `--task-id`。

```powershell
py -3 scripts/sc/llm_check_subtasks_coverage.py --task-id 17
```

#### 1.5 批量语义 gate（只读审计）：用一致性审计发现“语义偏差”任务清单

- `scripts/sc/llm_semantic_gate_all.py`
  - 意义：对所有任务（或指定任务集合）做“任务描述 vs acceptance 等价性”审计，输出 ok/needs_fix/unknown。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-semantic-gate-all/summary.json`。
  - 建议用法：
    - 首次全量扫：默认即可；
    - 对关键任务：用 `--consensus-runs 3` 降低单次模型抖动；必要时把 `--model-reasoning-effort` 提升到 `medium`。

```powershell
# 全量扫
py -3 scripts/sc/llm_semantic_gate_all.py

# 只审计关键任务（降低跑偏概率）
py -3 scripts/sc/llm_semantic_gate_all.py --task-ids 6,10,17 --consensus-runs 3 --model-reasoning-effort medium
```

### 2) Refs/test_refs 与测试证据（LLM + 确定性门禁）

#### 2.1 补齐 acceptance 的 `Refs:`（LLM）：把“语义条款”绑定到“可执行证据”

- `scripts/sc/llm_fill_acceptance_refs.py`
  - 意义：为 acceptance 条款补齐 `Refs:`（或重写明显 placeholder 的 Refs），并在 `--write` 时落盘到 `tasks_back.json/tasks_gameplay.json`。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-acceptance-refs/summary.json`。
  - 建议用法：
    - 单任务增量：`--task-id <id> --write --rewrite-placeholders --max-refs-per-item 2`；
    - 批量：先 dry-run，再逐批 `--write`；并用 `--max-tasks` 止损。

```powershell
# 单任务（推荐）
py -3 scripts/sc/llm_fill_acceptance_refs.py --task-id 17 --write --rewrite-placeholders --max-refs-per-item 2

# 批量（先 dry-run）
py -3 scripts/sc/llm_fill_acceptance_refs.py --all
py -3 scripts/sc/llm_fill_acceptance_refs.py --all --write --rewrite-placeholders --max-refs-per-item 2 --max-tasks 10
```

说明：只有当你明确要“重写已有 Refs”时才用 `--overwrite-existing`；否则会破坏已稳定的证据链。

#### 2.2 创建测试文件与红灯阶段（LLM；只生成 Refs 指向的文件）

- `scripts/sc/llm_generate_tests_from_acceptance_refs.py`
  - 意义：为 acceptance 条款中的 `Refs:` **明确指向但不存在**的测试文件生成内容（`.cs`/`.gd`），并在 prompt 中要求把 `ACC:T<id>.<n>` anchors 绑定到具体测试用例附近；最终在 refactor 阶段由 `scripts/python/validate_acceptance_anchors.py` 做硬门禁收口。可选跑 `scripts/sc/test.py` 做确定性验证。
  - 保守策略：只会创建 acceptance `Refs:` 里写明的路径；不会发明新路径/新文件名。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-acceptance-tests/`（prompt/trace/last output/verify log）。

建议参数与场景：

- 需要先制造“红灯”的任务（推荐）：
  - `--tdd-stage red-first`：LLM 选择一个“主 Ref”（偏好 `.cs`）并先生成一个**有意义且应当失败**的测试；其余 Refs 生成骨架（不刻意失败）。

- 需要顺手验证（推荐）：
  - `--verify unit`：仅跑单测（只要任务 Refs 不涉及 `.gd`）。
  - `--verify all`：跑 unit+Godot（当 Refs 涉及 `.gd` 时需要）。
  - `--verify auto`：脚本自动决定跑 unit/all；当涉及 `.gd` 时必须提供 `--godot-bin` 或设置环境变量 `GODOT_BIN`。

```powershell
# 典型：先红灯 + 自动验证（若包含 .gd 将转 all；需要 GODOT_BIN）
$env:GODOT_BIN="C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"

# 仅 Core 单测任务：红灯 + 只跑 unit
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit

# 只生成文件，不跑验证（加速；后续由 green/refactor/acceptance_check 收口）
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify none
```

#### 2.2.1 存量任务迁移工具（deterministic；可选）

- `scripts/sc/backfill_task_test_refs.py`
  - 意义：把 acceptance 条款中的 `Refs:`（证据文件）**确定性同步**到任务视图的 `test_refs`，并可选触发 LLM 生成缺失测试文件；只有加 `--write` 才会改写任务文件。
  - 输出：`logs/ci/<YYYY-MM-DD>/sc-backfill-test-refs/`。

- `scripts/python/backfill_acceptance_anchors_in_tests.py`
  - 意义：为存量任务的一批测试文件补齐 `ACC:T<id>.<n>` anchors（一次性迁移工具），用于把旧仓库拉到 `validate_acceptance_anchors.py` 的“方法级绑定”硬门禁口径。
  - 输出：`logs/ci/<YYYY-MM-DD>/backfill-acceptance-anchors/`。

- `scripts/python/check_sc_internal_imports.py`
  - 意义：止损检查，扫描 `scripts/sc/*.py` 的 `from _xxx import ...` 依赖，确保对应的 `scripts/sc/_xxx.py` 全部存在，避免同步漏文件导致入口脚本 ImportError。
  - 用法：`py -3 scripts/python/check_sc_internal_imports.py --out logs/ci/<YYYY-MM-DD>/sc-internal-imports.json`

#### 2.3 绿灯阶段（最小实现让测试变绿）

- `scripts/sc/build.py`（TDD 绿灯）
  - 命令：`py -3 scripts/sc/build.py tdd --task-id <id> --stage green`
  - 意义：在不扩大范围的前提下，让该任务证据范围内的 C# 测试变绿；默认带覆盖率门禁（lines≥90%、branches≥85%）。
  - 失败排障：查看 `logs/ci/<YYYY-MM-DD>/sc-build-tdd/`。

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

#### 2.4 重构阶段（命名/回链/契约一致性等硬门禁）

- `scripts/sc/build.py`（TDD 重构）
  - 命令：`py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor`
  - 意义：收口治理性硬门禁（命名、Refs/test_refs 回链、契约一致性、任务证据范围的测试命名 strict 等）。
  - 失败排障：查看 `logs/ci/<YYYY-MM-DD>/sc-build-tdd/`。

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

#### 2.5 完整确定性门禁（硬核部分，优先作为最终判定）

- `scripts/sc/acceptance_check.py`
  - 意义：可复现的确定性验收门禁（ADR/links/overlay/contracts/arch/security/quality/tests/perf/risk 等步骤）；可选要求“anchors 必须被本次执行证据证明已执行”。
  - 输出：默认写入 `logs/ci/<YYYY-MM-DD>/sc-acceptance-check/`；批量跑多个任务时建议加 `--out-per-task`，避免互相覆盖。

建议参数与场景：

- 只做局部复核（快）：用 `--only` 过滤步骤。
- 涉及 Godot `.gd` 测试：传 `--godot-bin`（或设置 `GODOT_BIN`）；需要把 headless 工件作为证据链时加 `--require-headless-e2e`。
- 需要“证据链严格”：加 `--require-task-test-refs` 与 `--require-executed-refs`。

```powershell
# 默认全跑（确定性）
py -3 scripts/sc/acceptance_check.py --task-id <id> --out-per-task

# 涉及 Godot 测试 + 性能硬门禁（p95）
$env:GODOT_BIN="C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"
py -3 scripts/sc/acceptance_check.py --task-id <id> --out-per-task --godot-bin "$env:GODOT_BIN" --perf-p95-ms 20

# 证据链更严格（需要 anchors 被本次执行证明）
py -3 scripts/sc/acceptance_check.py --task-id <id> --out-per-task --require-task-test-refs --require-executed-refs

# 只跑 links+tests（用于快速回归）
py -3 scripts/sc/acceptance_check.py --task-id <id> --out-per-task --only links,tests
```

#### 2.6 LLM 软审查（结构化模板；用确定性证据约束跑偏）

- `scripts/sc/llm_review.py`
  - 意义：基于 diff + 任务上下文 +（已生成的）`sc-acceptance-check` 工件做软审查，输出“风险/建议/缺口”清单；用于发现确定性门禁未覆盖的语义缺口。
  - 模板：`scripts/sc/templates/llm_review/bmad-godot-review-template.txt`

建议参数与场景：

- 想锁定提交（降低跑偏）：`--task-id <id> --auto-commit`（要求 commit message 含 `Task [<id>]`）。
- 只审查当前改动：`--uncommitted`。
- 只生成 prompts 排障：`--prompts-only`。
- 两段式 gate（可选）：`--semantic-gate warn|require` 让 LLM 语义 gate 成为“软/硬”附加步骤（在确定性 acceptance_check 之后）。

```powershell
# 典型：按 Godot 模板做软审查（锁定最近 Task commit）
py -3 scripts/sc/llm_review.py --task-id <id> --auto-commit --review-template scripts/sc/templates/llm_review/bmad-godot-review-template.txt --model-reasoning-effort medium

# 只审查未提交改动
py -3 scripts/sc/llm_review.py --task-id <id> --uncommitted --review-template scripts/sc/templates/llm_review/bmad-godot-review-template.txt
```

### 3) 测试命名门禁（止损策略）

- `scripts/python/check_test_naming.py`
  - 意义：检查 `Game.Core.Tests` 的测试命名（Given_When_Then/Should_），避免“测试存在但不可读、不可复用”。
  - 建议用法：
    - 任务级 strict（推荐）：只检查该任务 `test_refs` 指向的 `.cs` 测试；
    - 全仓 legacy：仅观察，不建议硬卡。

```powershell
py -3 scripts/python/check_test_naming.py --task-id <id> --style strict
py -3 scripts/python/check_test_naming.py --style legacy
```

## 注意事项

- 这套链路的本质是：先把"语义义务"收敛到 `acceptance`（并把非义务迁到 `test_strategy/details`），再让 `Refs:` 把每条义务绑定到可执行证据。
- `llm_extract_task_obligations.py` 与 `llm_check_subtasks_coverage.py` 都是"单任务诊断工具"，请总是显式传 `--task-id`，避免 tasks.json 没有 in-progress 时默认选择失败。
- LLM 脚本只负责生成/建议，最终以确定性门禁（`scripts/sc/acceptance_check.py` + `scripts/sc/test.py`）通过为准。
- `scripts/sc/build.py tdd --generate-red-test` 与 `scripts/sc/llm_generate_red_test.py` 都会生成 `Game.Core.Tests/Tasks/Task<id>RedTests.cs` 作为临时红灯文件；进入 `--stage refactor` 前必须迁移/删除，避免被硬门禁拦截。

## 附录：LLM 与验收相关脚本索引

本附录的目标是：把“LLM 相关脚本 + acceptance 相关脚本”作为一份可执行索引固定下来，避免工作流升级后口径漂移。

约定：

- `Refs:`：acceptance 条款里指向的测试文件路径（仓库根目录相对路径）。
- `test_refs`：任务级证据清单（视图任务文件中的字段），用于限定“该任务的测试证据范围”。
- `ACC:T<id>.<n>`：验收 anchors，用于把 acceptance 条款绑定到具体测试方法/用例附近。
- `run_id`：一次 `scripts/sc/test.py` 执行的唯一标识，用于把“本次执行”与 TRX/JUnit/审计 JSONL 证据绑定。

### A. LLM 脚本（`scripts/sc/llm_*.py`）

#### A1) `scripts/sc/llm_extract_task_obligations.py`

- 意义：单任务“义务抽取 + 覆盖诊断”（obligations vs acceptance）。用于发现“任务细节/子任务里说了，但 acceptance 没写”的缺口。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-obligations-task-<id>/`（`summary.json`、`verdict.json`、`report.md`、prompt/trace）。
- 场景：任务被判 done 但仍出现语义缺口；或你想在补 acceptance 前先定位义务列表。
- 关键参数：
  - `--task-id <id>`：建议总是显式传入（当 tasks.json 没有 in-progress 时默认选择会失败）。
  - `--timeout-sec`：单次 LLM 调用超时。
  - `--max-prompt-chars`：止损 prompt 体积。

#### A2) `scripts/sc/llm_align_acceptance_semantics.py`

- 意义：批量对齐 acceptance 语义（acceptance-only phase）。目标是让“任务描述 ↔ acceptance 集合”尽量等价。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-align-acceptance-semantics/summary.json`（逐任务变更/失败信息）。
- 场景：新生成三份任务文件后，先把 acceptance 补到不贫血；或对 done 任务做止损式补齐。
- 关键参数：
  - `--scope all|done|not-done`：作用域。
  - `--task-ids <csv>`：只对部分任务处理。
  - `--apply`：落盘（不带则 dry-run）。
  - `--preflight-migrate-optional-hints`：调用确定性脚本把 `tasks.json` 里的 demo/可选项迁到视图 `test_strategy`，避免污染 acceptance。
  - `--append-only-for-done`：done 任务止损模式（只追加，不重写）。
  - `--semantic-findings-json <path>`：可选注入 `sc-semantic-gate-all/summary.json` 作为提示。

- 链接脚本（该脚本会间接触发）：
  - `scripts/python/migrate_task_optional_hints_to_views.py`：当启用 preflight 时调用。

#### A3) `scripts/sc/llm_check_subtasks_coverage.py`

- 意义：单任务 subtasks 覆盖检查（subtasks title+details 是否被 acceptance 覆盖）。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-subtasks-coverage-task-<id>/`（`summary.json`、`verdict.json`、`report.md`）。
- 场景：主任务通过但子任务义务被漏掉（典型：T17.x）。
- 关键参数：
  - `--task-id <id>`：建议总是显式传入。
  - `--timeout-sec` / `--max-prompt-chars`：止损。

#### A4) `scripts/sc/llm_semantic_gate_all.py`

- 意义：批量语义 gate（任务描述 vs acceptance 等价性审计），输出 ok/needs_fix/unknown。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-semantic-gate-all/summary.json`。
- 场景：全仓收敛；或只对一批任务做复核，得到 needs_fix 列表。
- 关键参数：
  - `--task-ids <csv>`：只审计指定任务。
  - `--batch-size`：每次 LLM 调用包含的任务数。
  - `--consensus-runs`：同一 batch 重跑 N 次做多数表决（降抖）。
  - `--model-reasoning-effort low|medium|high`：推理强度止损开关。
  - `--max-acceptance-items`：限制每个视图纳入 prompt 的 acceptance 数量。

#### A5) `scripts/sc/llm_fill_acceptance_refs.py`

- 意义：为 acceptance 条款补齐/改写 `Refs:`（证据绑定），只改任务视图文件（`tasks_back.json/tasks_gameplay.json`）。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-acceptance-refs/summary.json`。
- 场景：acceptance 已经语义对齐，但缺少 `Refs:` 或存在 placeholder Refs。
- 关键参数：
  - `--task-id <id>` / `--all`：单任务或批量。
  - `--write`：落盘（不带则 dry-run）。
  - `--rewrite-placeholders`：仅当 Refs 像占位符时重写（推荐）。
  - `--overwrite-existing`：强制重写已有 Refs（高风险，慎用）。
  - `--max-refs-per-item`：每条 acceptance 限制最多 refs 数量（默认 2）。

#### A6) `scripts/sc/llm_generate_tests_from_acceptance_refs.py`

- 意义：只为 acceptance `Refs:` **明确指向但不存在**的测试文件生成内容（`.cs`/`.gd`），并在 prompt 中要求把 `ACC:T<id>.<n>` 写入对应测试用例附近；refactor 阶段由 `scripts/python/validate_acceptance_anchors.py` 证明绑定。可选跑 `scripts/sc/test.py` 验证。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-acceptance-tests/`（prompt/trace/verify log）。
- 场景：你已经补齐 `Refs:`，希望自动生成缺失测试文件，并进入 TDD red/green/refactor。
- 关键参数：
  - `--task-id <id>`：必填。
  - `--tdd-stage normal|red-first`：`red-first` 会先生成一个主 Ref 的“有意义红灯”。
  - `--verify none|unit|all|auto`：验证级别；涉及 `.gd` 时 `all/auto` 需要 `--godot-bin` 或环境变量 `GODOT_BIN`。
  - `--timeout-sec`：单文件 LLM 超时；`--select-timeout-sec`：主 Ref 选择超时。

- 链接脚本（该脚本会触发）：
  - `scripts/python/validate_acceptance_refs.py`：生成前会先做 `Refs:` 语法门禁。
  - `scripts/sc/analyze.py`：生成 `task_context` 作为 prompt 上下文。
  - `scripts/sc/test.py`：当 `--verify` 非 none 时会调用。

#### A7) `scripts/sc/llm_generate_red_test.py`

- 意义：生成 `Game.Core.Tests/Tasks/Task<id>RedTests.cs` 红灯文件（临时骨架/或更有意义的红灯），可选自动跑 red 阶段。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-llm-red-test/`。
- 场景：你不想批量生成所有 Refs 测试，只想先有一个“能失败的红灯入口”。
- 关键参数：
  - `--task-id <id>`：必填。
  - `--verify-red`：写入后调用 `sc-build tdd --stage red` 验证红灯。

#### A8) `scripts/sc/llm_review.py`

- 意义：LLM 软审查。它会读取 diff + 任务上下文，并注入确定性 `sc-acceptance-check` 工件，输出“风险/建议/缺口”清单。
- 模板：`scripts/sc/templates/llm_review/bmad-godot-review-template.txt`
- 输出：当提供 `--task-id` 时写入 `logs/ci/<YYYY-MM-DD>/sc-llm-review-task-<id>/`；否则写入 `logs/ci/<YYYY-MM-DD>/sc-llm-review/`。
- 场景：确定性门禁通过，但你仍担心语义缺口/架构风险；或想把 BMAD checklist 结构化注入审查。
- 关键参数：
  - `--review-profile bmad-godot` 或 `--review-template <path>`：选择模板。
  - `--task-id <id> --auto-commit`：锁定最近一次包含 `Task [<id>]` 的提交（降低跑偏）。
  - `--uncommitted`：审查未提交改动。
  - `--semantic-gate skip|warn|require`：两段式（在 deterministic acceptance_check 之后追加 LLM 语义 gate）。
  - `--model-reasoning-effort`：推理强度。

### B. 验收与证据链主干（确定性 + TDD）

#### B1) `scripts/sc/analyze.py`

- 意义：生成任务上下文（triplet 合并），给后续 red/green/refactor/LLM prompt 使用。
- 输出：`logs/ci/<YYYY-MM-DD>/sc-analyze/task_context.<id>.json` 与 `task_context.<id>.md`。
- 常用参数：
  - `--task-id <id>`：建议总是显式传入。
  - `--taskdoc-dir taskdoc`：可选补充 Serena 导出的上下文。
  - `--focus all|quality|security|performance|architecture`：缩小扫描面。
  - `--format text|json|report`：输出格式。

#### B2) `scripts/sc/test.py`

- 意义：统一的测试入口（unit/e2e/all），并生成 `run_id` 供证据绑定。
- 常用参数：
  - `--type unit|e2e|all`：类型。
  - `--godot-bin <path>`：跑 e2e/all 必需。
  - `--run-id <id>`：可选手工绑定（默认自动生成）。
  - `--no-coverage-gate`：止损开关（不建议默认开启）。

- 链接脚本：
  - `scripts/python/run_dotnet.py`：dotnet test/coverage 产出。
  - `scripts/python/run_gdunit.py`：GdUnit4 headless 产出。
  - `scripts/python/smoke_headless.py`：Godot headless smoke。

#### B3) `scripts/sc/build/tdd.py`（通过 `scripts/sc/build.py tdd` 触发）

- 意义：TDD gatekeeper（red/green/refactor）。前置 analyze+必填字段校验；refactor 强制 Refs/test_refs/命名等硬门禁。
- 关键参数：
  - `--stage red|green|refactor`
  - `--task-id <id>`
  - `--generate-red-test`：缺测试时生成 `Task<id>RedTests.cs`（临时红灯文件）。
  - `--no-coverage-gate`：止损开关（不建议默认开启）。

- 链接脚本（refactor/阶段前置会触发）：
  - `scripts/python/validate_task_context_required_fields.py`
  - `scripts/python/validate_acceptance_refs.py`
  - `scripts/python/validate_acceptance_anchors.py`
  - `scripts/python/update_task_test_refs_from_acceptance_refs.py`
  - `scripts/python/validate_task_test_refs.py`
  - `scripts/python/check_test_naming.py`

#### B4) `scripts/sc/acceptance_check.py`

- 意义：可复现的确定性验收门禁（ADR/links/overlay/contracts/arch/security/tests/perf/risk 等）。默认“安全/路径/SQL/审计 schema”是 require。
- 输出：
  - 默认：`logs/ci/<YYYY-MM-DD>/sc-acceptance-check/`
  - 批量：建议加 `--out-per-task` 输出到 `sc-acceptance-check-task-<id>/` 防止覆盖。
- 关键参数（常用）：
  - `--only <steps>`：只跑指定步骤（如 `links,tests`）。
  - `--godot-bin`：涉及 `.gd`/e2e 时需要。
  - `--perf-p95-ms 20`：解析 headless.log 的 p95 作为硬门禁。
  - `--require-task-test-refs`：要求 `test_refs` 非空。
  - `--require-executed-refs`：要求 anchors 的“本次执行证据”（TRX/JUnit）。
  - `--subtasks-coverage skip|warn|require`：子任务覆盖 gate。

当前 `scripts/sc/acceptance_check.py` 的 risk 步骤会把风险结果汇总到该次验收的 `summary.json` 里（通过 `--only risk` 可单独运行），目前不会单独生成 `risk_summary.json` 文件。

- 说明：验收步骤编排在 `scripts/sc/_acceptance_steps.py`，其中会调用下述确定性脚本（见 C 节）。

### C. acceptance_check 链接的确定性子脚本（建议只在排障时单独跑）

这些脚本大多以 `--out <path>` 输出 JSON 报告（建议写入 `logs/ci/<YYYY-MM-DD>/...`），并由 `acceptance_check.py` 统一编排。

#### C1) Refs/anchors/证据绑定

- `scripts/python/validate_acceptance_refs.py`
  - 作用：校验 acceptance 条款的 `Refs:`（把自由文本变成可确定性校验）。规则包含：
    - 每条 acceptance 必须包含 `Refs:`；
    - Refs 必须是 repo 相对路径，且只能是允许的测试根目录前缀（`Game.Core.Tests/`、`Tests.Godot/tests/`、`Tests/`）下的 `.cs`/`.gd`；
    - 文本↔Refs 类型一致性硬规则：
      - 文本提到 xUnit ⇒ Refs 至少包含一个 `.cs`；
      - 文本提到 GdUnit4 ⇒ Refs 至少包含一个 `.gd`；
      - 文本提到 Game.Core ⇒ Refs 至少包含一个 `Game.Core.Tests/*.cs`；
    - refactor 阶段：引用文件必须存在，且每个 ref 必须包含在该任务的 `test_refs` 里（证据链闭环）。
  - 参数：`--task-id <id> --stage red|green|refactor --out <json>`。

说明："最多 5 行" 是为了避免 anchor 漂在文件顶部/注释区导致绑定不确定。

补充：如果你希望放宽到"30 行内"（你之前提出的建议值），需要修改 `scripts/python/validate_acceptance_anchors.py` 内部常量（当前无 CLI 参数）。


- `scripts/python/validate_acceptance_anchors.py`
  - 作用：校验 `ACC:T<id>.<n>` anchors，提供确定性的"语义绑定"（避免 acceptance 只写了 Refs，但测试里没有声明覆盖）。
  - 绑定规则（确定性，当前实现口径）：
    - 对 task T<id> 的 acceptance 第 n 条（1-based），anchor 固定为 `ACC:T<id>.<n>`；
    - refactor 阶段：至少一个 Refs 指向的测试文件必须包含该 anchor；
    - refactor 阶段还要求"方法级绑定"：anchor 出现位置后"近距离"必须出现测试用例标记：
      - C#：在 anchor 行之后最多 5 行内出现 `[Fact]` 或 `[Theory]`；
      - GDScript（GdUnit4）：在 anchor 行之后最多 5 行内出现 `func test_...`；
    - red/green 阶段：该门禁只做 skip（不阻断），让你先生成/跑通测试后再收口。
  - 参数：`--task-id <id> --stage red|green|refactor --out <json>`。

- `scripts/python/validate_acceptance_execution_evidence.py`
  - 作用：校验 TRX/JUnit 证据里能证明本次执行覆盖了对应 anchors（run_id 绑定）。
  - 参数：`--task-id <id> --run-id <id> --out <json> [--date YYYY-MM-DD]`。

#### C2) 任务证据清单（test_refs）

- `scripts/python/update_task_test_refs_from_acceptance_refs.py`
  - 作用：把 acceptance `Refs:` 同步进任务 `test_refs`（replace/merge）。
  - 参数：`--task-id <id> [--mode replace|merge] [--write]`。

- `scripts/python/validate_task_test_refs.py`
  - 作用：校验 `test_refs` 字段；可启用 `--require-non-empty`。
  - 参数：`--task-id <id> --out <json> [--require-non-empty]`。

- `scripts/python/check_test_naming.py`
  - 作用：C# 单测命名门禁（Given/When/Then 或 Should_）；可限定到任务证据范围。
  - 参数：`--style legacy|strict [--task-id <id>]`。

#### C3) 回链与 Overlay

- `scripts/python/task_links_validate.py`
  - 作用：回链一键校验（内部调用 `check_tasks_back_references.py` 与 `check_tasks_all_refs.py`）。

- `scripts/python/validate_task_overlays.py`
  - 作用：校验 tasks 中 overlay_refs 与 `ACCEPTANCE_CHECKLIST.md` Front Matter。
  - 参数：`[--task-file <path>]`。

- `scripts/python/validate_overlay_test_refs.py`
  - 作用：校验单个 overlay Markdown 的 `Test-Refs` 区块是否存在且路径可解析。
  - 参数：`--overlay <path> --out <json>`。

- `scripts/python/validate_contracts.py`
  - 作用：校验 overlay 文档中引用的 contract 文件存在，并确认 overlays 有链接到 Contracts 目录。
  - 参数：`[--root <dir>]`。

#### C4) 架构边界与契约快速体检

- `scripts/python/check_architecture_boundary.py`
  - 作用：检查 `Game.Core` 不应依赖 Godot API 等架构边界约束。
  - 参数：`--out <json>`。

- `scripts/python/check_domain_contracts.py`
  - 可选：业务域契约一致性检查入口（模板仓不内置具体域规则，避免耦合）。
  - 建议约定：检查 `Game.Core/Contracts/<Domain>/**` 下的事件/DTO 命名、必填字段、版本演进规则；输出 JSON 到 stdout 供 CI 归档。

#### C5) 安全硬门/软扫（静态）与运行证据

- `scripts/python/security_hard_path_gate.py`
  - 作用：路径安全不变量静态扫描（默认 hard gate）。
  - 参数：`--out <json>`。

- `scripts/python/security_hard_sql_gate.py`
  - 作用：SQL 注入反模式静态扫描（默认 hard gate）。
  - 参数：`--out <json>`。

- `scripts/python/security_hard_audit_gate.py`
  - 作用：安全审计日志存在性与 schema 字段静态扫描（默认 hard gate）。
  - 参数：`--out <json>`。

- `scripts/python/security_soft_scan.py`
  - 作用：启发式安全 soft scan（不一定 hard fail）。
  - 参数：`--out <json>`。

- `scripts/python/validate_security_audit_execution_evidence.py`
  - 作用：校验本次 run_id 对应的 `security-audit.jsonl` 运行证据存在（run_id 绑定）。
  - 参数：`--run-id <id> --out <json> [--date YYYY-MM-DD]`。

#### C6) UI 事件治理（可选 gate）

- `scripts/python/validate_ui_event_json_guards.py`
  - 作用：UI 事件 JSON 解析守卫（大小/深度等）静态扫描。
  - 参数：`--out <json>`。

- `scripts/python/validate_ui_event_source_verification.py`
  - 作用：UI 事件 handler 若携带 `source`，要求被使用/校验（静态扫描）。
  - 参数：`--out <json>`。

#### C7) 其它常见确定性辅助

- `scripts/python/check_encoding.py`
  - 作用：编码/换行审计（避免 UTF-8/CRLF 噪音）。
  - 参数：`--since-today` / `--since <date>` / `--files ...` / `--root <dir>`。

- `scripts/python/check_sentry_secrets.py`
  - 作用：检查 Sentry secrets 是否意外写入仓库或被上传执行（确定性安全自检）。
  - 参数：无（直接输出结果）。

### D. 建议执行顺序（简版）

- 语义（acceptance-only）：
  1) `scripts/python/migrate_task_optional_hints_to_views.py --write`（可选）
  2) `scripts/sc/llm_align_acceptance_semantics.py --apply`
  3) `scripts/sc/llm_check_subtasks_coverage.py --task-id <id>`（有 subtasks 时）
  4) `scripts/sc/llm_semantic_gate_all.py`（批量审计）

- 证据（Refs/test + TDD + 硬门）：
  1) `scripts/sc/llm_fill_acceptance_refs.py --task-id <id> --write --rewrite-placeholders`
  2) `scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"`
  3) `py -3 scripts/sc/build.py tdd --task-id <id> --stage green`
  4) `py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor`
  5) `py -3 scripts/sc/acceptance_check.py --task-id <id> --out-per-task --godot-bin "$env:GODOT_BIN" --perf-p95-ms 20`
  6) `py -3 scripts/sc/llm_review.py --task-id <id> --auto-commit --review-template scripts/sc/templates/llm_review/bmad-godot-review-template.txt`

## 0) Delta alignment (2026-02)

- `acceptance_check.py`: strengthened with `--security-profile`, `--require-task-test-refs`, `--require-executed-refs`, `--subtasks-coverage`, and `--out-per-task`.
- `llm_review.py`: profile-aware risk context and task-scoped output path behavior.
- `llm_extract_task_obligations.py`: stability controls via `--consensus-runs`, `--garbled-gate`, `--auto-escalate`.
- `llm_check_subtasks_coverage.py`: supports `--consensus-runs`.
- `llm_semantic_gate_all.py`: supports `--garbled-gate` precheck.
- CI invariant: emit `SecurityProfile: <host-safe|strict>` in Step Summary.
