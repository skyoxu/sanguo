# BMAD 与本仓库工作流的协作方式

本文档说明在本仓库中，BMAD（BMad-Method）除了产出 PRD/架构文档之外，如何与现有脚本工作流（`acceptance_check.py` / `llm_review.py` / 任务三联文件）协作。

## 1. 安装与校验（Windows）

本仓库推荐将 BMAD 安装在仓库上层目录（便于多项目共享），例如：

- BMAD 根目录：`C:\buildgame`
- 本仓库路径：`C:\buildgame\sanguo`

本地校验命令：

- `py -3 scripts/python/bmad_verify_installation.py`
- 强制要求安装 Godot 扩展包：`py -3 scripts/python/bmad_verify_installation.py --require-expansion bmad-godot-game-dev`

说明：

- `bmad` 官方安装器在有核心升级提示时可能进入交互模式；本仓库不依赖交互式步骤才能运行 CI。
- 校验脚本只做“存在性 + 证据落盘（logs/ci/**）”，不下载/不修改任何文件。

## 2. 作为 llm_review.py 的结构化审查模板（软门禁）

目标：把 BMAD 的“多角色审查清单”能力转化为本仓库可复用的结构化模板，降低 LLM 复核时的跑偏概率。

本仓库实现方式：

- 模板文件：`scripts/sc/templates/llm_review/bmad-godot-review-template.txt`
- 启用模板：`py -3 scripts/sc/llm_review.py --review-profile bmad-godot ...`

原则：

- 仍以 `acceptance_check.py` 的确定性证据链为主（硬门禁）；LLM 仅对“语义等价/测试强度/边界遗漏”做解释与建议。
- 模板不依赖机器上 BMAD 的安装路径（避免 CI 环境不一致）。

## 3. 参与“任务语义 → 验收条款”的上游治理（黑名单策略）

目标：避免把“演示路径 / 本地 demo / 可选加固建议”等非核心内容混入 `tasks.json` 的 `details/testStrategy`，进而污染 `acceptance[]` 的语义对齐与门禁判断。

策略：黑名单（只规定哪些必须迁移到视图文件；未命中的内容默认允许保留在验收语义体系里）。

落地：

- 迁移脚本：`scripts/python/migrate_task_optional_hints_to_views.py`
  - 从 `.taskmaster/tasks/tasks.json` 的 `details/testStrategy` 中识别“可选项/演示路径/加固建议”等行
  - 迁移到视图文件 `.taskmaster/tasks/tasks_back.json` 与 `.taskmaster/tasks/tasks_gameplay.json` 的 `test_strategy`，并强制加 `Optional:` 前缀
- 接入点：`scripts/sc/llm_align_acceptance_semantics.py`
  - 当执行 `--apply` 时，默认先跑一次上述迁移（可用 `--skip-preflight-migrate-optional-hints` 禁用）

这样做的收益：

- `acceptance[]` 更聚焦“可证伪的行为义务”，减少“done 不真实”的来源
- `test_strategy/details` 保留演示/加固线索，但不会变成强制验收条款

