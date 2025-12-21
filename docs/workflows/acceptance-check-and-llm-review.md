# Acceptance Check 与 LLM Review：为何创建、如何演进、如何使用

本文件记录两个脚本的动机、演进与使用方式：

- `scripts/sc/acceptance_check.py`：确定性“验收门禁”（目标对齐 Claude Code 的 `/acceptance-check`）
- `scripts/sc/llm_review.py`：可选的“LLM 口头审查”（用于模拟 6 个 subagent 的审查视角，但默认不阻断）

> 约束：Windows-only；所有输出统一落盘到 `logs/`（便于取证与排障）；脚本与文档均使用 UTF-8。

---

## 1. 背景与动机（为什么要做）

### 1.1 现实问题

在 Claude Code 中，我可以用 `/acceptance-check` 触发多 Subagent 编排式验收；但在 Codex CLI 中：

- 不依赖“聊天上下文”的可复现门禁更可靠（尤其是任务推进到后期，约束和证据要落盘可追溯）。
- “口头审查”很容易受网络/模型/限流/空输出影响，不能作为唯一质量门禁。

因此需要在仓库内提供：

1) **确定性、可复现、可审计**的验收门禁脚本（替代 Subagent 的“阻断性判定”部分）  
2) **可选**的 LLM 审查脚本（替代 Subagent 的“建议性审查”部分），并默认不阻断（止损）

### 1.2 设计原则（止损优先）

- **硬门禁必须确定性**：构建/测试/回链/契约一致性/架构边界等，必须脚本化并可复现。
- **LLM 只做软证据**：只做补充意见与留痕，不作为默认阻断（除非显式 `--strict`）。
- **输出落盘**：所有检查写入 `logs/ci/<YYYY-MM-DD>/...`，便于对比、归档和排障。

---

## 2. `acceptance_check.py` 做什么（确定性验收门禁）

### 2.1 目标与定位

`scripts/sc/acceptance_check.py` 提供“等价于 `/acceptance-check` 的验收门禁”，但实现方式是：

> 不调用 LLM Subagent；把“6 个 subagent 的关注点”映射为仓库中可执行的确定性检查。

### 2.2 输入与默认行为

- “当前任务”默认来自 `.taskmaster/tasks/tasks.json` 中第一个 `status == "in-progress"` 的任务。
- 可用 `--task-id <n>` 显式指定任务。
- 会读取三份任务信息并合并为 triplet 上下文：
  - `tasks.json.master.tasks[].id`
  - `tasks_back[].taskmaster_id`
  - `tasks_gameplay[].taskmaster_id`
- 若存在 `taskdoc/<id>.md` 会作为附加上下文被记录在报告中（用于追溯）。

### 2.3 输出与退出码

- 输出目录：`logs/ci/<YYYY-MM-DD>/sc-acceptance-check/`
  - `summary.json`：机器可读汇总
  - `report.md`：人可读报告
  - 各 step 的 `.log/.json` 工件（如 `perf-budget.json`）
- 退出码：
  - `0`：所有硬门禁通过
  - `1`：至少一项硬门禁失败
  - `2`：用法错误/缺少关键依赖

### 2.4 检查项概览（映射“6 subagent”关注点）

硬门禁（失败即阻断）：

- ADR 合规：任务 `adrRefs/archRefs/overlay` 是否完整；ADR 文件存在；至少引用 ≥1 个 **Accepted** ADR
- 任务回链：`py -3 scripts/python/task_links_validate.py`
- Overlay 校验：`py -3 scripts/python/validate_task_overlays.py`
- 契约一致性：`py -3 scripts/python/validate_contracts.py`
- 架构边界：`Game.Core/**` 不得引用 `Godot.*`
- 构建门禁：`dotnet build -warnaserror`（通过 sc build 入口）
- 测试门禁：`py -3 scripts/sc/test.py --type all`（含 xUnit + GdUnit4 + smoke）

软门禁（不阻断，只记录证据）：

- Sentry secrets/编码扫描/核心契约检查（输出写入 `security-soft.json`）

性能门禁（可选硬门禁）：

- 解析最新 `logs/ci/**/headless.log` 中的 `[PERF] ... p95_ms=...`，与阈值比较（口径见 ADR-0015）

### 2.5 性能门禁如何启用（硬门禁）

默认**不启用**（避免在 CI/机器差异下误伤）。启用方式：

- 显式启用：  
  `py -3 scripts/sc/acceptance_check.py --task-id 10 --godot-bin "$env:GODOT_BIN" --perf-p95-ms 20`
- 或设置环境变量：  
  `$env:PERF_P95_THRESHOLD_MS = "20"`
- legacy 快捷开关：  
  `--require-perf`（阈值取 `PERF_P95_THRESHOLD_MS`，否则默认 20ms；仍建议优先用 `--perf-p95-ms` 明示）

注意：

- 如果只跑 `--only perf`，脚本不会自动跑 smoke 生成 `headless.log`，你需要先运行一次：
  - `py -3 scripts/sc/test.py --type all --godot-bin "$env:GODOT_BIN"`  
  或  
  - `py -3 scripts/python/smoke_headless.py --godot-bin "$env:GODOT_BIN" --project . --scene res://Game.Godot/Scenes/Main.tscn --timeout-sec 5 --mode strict`

---

## 3. `llm_review.py` 做什么（可选 LLM 口头审查）

### 3.1 目标与定位

`scripts/sc/llm_review.py` 用来模拟“6 个 subagent 口头审查”的体验：

- 为每个角色生成一份审查输出，并落盘
- 默认 **soft**：即使 LLM 失败/空输出，也不会阻断（返回 `warn`），避免被网络/限流卡死

它不替代 `acceptance_check.py`，只补充“建议性意见与留痕”。

### 3.2 Prompt 来源（关键：读取你的 Claude agents）

脚本会加载以下 prompt（按优先级）：

1) 仓库内 `.claude/agents/*.md`（项目特定）
   - `adr-compliance-checker`
   - `performance-slo-validator`
2) 用户目录的 lst97 四件套（社区 subagent）
   - 默认路径：`%USERPROFILE%\\.claude\\agents\\lst97\\*.md`
   - 可覆盖：`--claude-agents-root "C:\\Users\\weiruan\\.claude\\agents"` 或环境变量 `CLAUDE_AGENTS_ROOT`

在输出的 `summary.json` 中会记录 `agent_prompt_source`，你可以核对是否真的读到了预期文件。

### 3.3 输入、输出与状态

输入（选择一种 diff 视角）：

- 对比某个 base：`--base main`（默认）
- 审查未提交改动：`--uncommitted`
- 审查某个提交：`--commit <sha>`

输出目录：`logs/ci/<YYYY-MM-DD>/sc-llm-review/`

- `review-<agent>.md`：每个角色的最终输出（`codex exec --output-last-message`）
- `prompt-<agent>.md`：实际送入 LLM 的提示词（含 diff，做了截断）
- `trace-<agent>.log`：执行痕迹（便于排障）
- `summary.json`：汇总（`ok|warn|fail`）

默认状态语义：

- `ok`：LLM 调用成功且输出非空
- `skipped`：调用失败/超时/空输出（默认不阻断）
- `fail`：仅在 `--strict` 时出现（会阻断）

### 3.4 用法示例（Windows）

```powershell
# 1) 对比当前分支 vs main（最常用）
py -3 scripts/sc/llm_review.py --task-id 10 --base main

# 2) 审查未提交改动
py -3 scripts/sc/llm_review.py --task-id 10 --uncommitted

# 3) 指定只跑部分角色
py -3 scripts/sc/llm_review.py --task-id 10 --base main --agents adr-compliance-checker,security-auditor

# 4) 覆盖 Claude agents 根目录（可选）
py -3 scripts/sc/llm_review.py --task-id 10 --base main --claude-agents-root "C:\Users\weiruan\.claude\agents"

# 5) 强制硬门禁（不建议：会被网络/空输出误伤）
py -3 scripts/sc/llm_review.py --task-id 10 --base main --strict
```

---

## 4. 推荐工作流（止损版）

每完成一个 `tasks.json` 的任务（或一个子任务提交）后：

1) **硬门禁**：  
   `py -3 scripts/sc/acceptance_check.py --task-id <id> --godot-bin "$env:GODOT_BIN" --perf-p95-ms 20`
2) **软审查（可选）**：  
   `py -3 scripts/sc/llm_review.py --task-id <id> --base main`
3) 通过后再进入下一个任务（避免质量债滚雪球）。

---

## 5. 演进与优化记录（重要变更点）

### 5.1 `acceptance_check.py` 的演进

- 初版：提供确定性门禁与落盘报告（`summary.json`/`report.md`），并接入 `Windows Quality Gate`。
- 优化：性能门禁从“仅检查 perf 工件存在”升级为**可配置硬门禁**：
  - 直接解析 `logs/ci/**/headless.log` 的 `[PERF] ... p95_ms=...`
  - 阈值口径参考 `ADR-0015`（CI 建议 20ms；目标 16.67ms）

### 5.2 `llm_review.py` 的演进

- 早期尝试使用 `codex review` 组合 `--base` + stdin prompt，发现 CLI 参数限制不可行；
- 改为使用 `codex exec`，并把 `git diff`（可截断）嵌入 prompt，保证可用性；
- 增加“读取用户目录 lst97 prompt”的能力，尽量贴近 Claude 的 4 个社区 subagent；
- 默认 soft（`warn`）防止网络/空输出导致流程被阻断。

---

## 6. 这套“等价 /acceptance-check”实现改动了哪些文件？

实现 `acceptance_check` 等价门禁时，**不止**创建脚本文件，还调整了文档与 CI：

- 新增：`scripts/sc/acceptance_check.py`
- 更新：`scripts/sc/README.md`（补充用法与产物说明）
- 更新：`.github/workflows/windows-quality-gate.yml`（在 Quality Gate 中运行 acceptance-check）

后续为了补齐“LLM 口头审查”等价体验，又新增/更新：

- 新增：`scripts/sc/llm_review.py`
- 更新：`scripts/sc/README.md`（补充 llm_review 与 Claude agents 读取口径）

> 说明：以上文件均属于“工具链/工作流层”，不应与游戏业务逻辑耦合。

