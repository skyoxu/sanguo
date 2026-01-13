# 从任务视图驱动首个 T2 场景实现（sanguo）

> 本文档面向当前仓库 `sanguo`（Godot 4.5 + C#，Windows-only）。  
> 目标：把“首个 T2 可玩闭环”从“能跑”收敛为“可审计、可复核、可自动化取证”的证据链。

## 1. 先用 PRD + Overlay 锁定 T2 场景流（避免返工）

- PRD（输入 SSoT）：`.taskmaster/docs/prd.txt`
  - T2 最小可玩闭环描述
  - T50–T60 骨架拆解草案（模块范围/非目标/确定性输入/事件 type+触发点/ACC）
- Overlay（纵切 SSoT）：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - 玩法闭环：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - T50–T60 概览：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md`
  - T50–T60 拆页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-t50-*.md` … `08-t60-*.md`
- Checklist（验收入口）：`docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`

止损原则：

- Overlay 08 只引用 Base/ADR 口径，不复制阈值/策略，不在文档里散落“魔法字段定义”。  
- 任何会落地为代码/测试的改动，必须引用 ≥1 条 Accepted ADR（至少 ADR-0004/ADR-0005/ADR-0019 之一，按任务类型选）。

## 2. 以任务视图为语义 SSoT（不要用 tasks.json 猜）

本仓库的“可执行语义验收”以任务视图为准：

- 全量视图：`.taskmaster/tasks/tasks_back.json`
- 玩法视图：`.taskmaster/tasks/tasks_gameplay.json`

关键字段含义（建议统一用法）：

- `acceptance[]`：必须可证伪的验收条款（每条都要能被测试证明）。
- `test_refs[]`：证据清单（应包含 acceptance 里所有 `Refs:` 的并集）。
- `contractRefs[]`：本任务关心的领域事件 `EventType`（ADR-0004），用于契约对齐与避免重复造轮子。
- `adr_refs[]` / `chapter_refs[]` / `overlay_refs[]`：回链（用于确定性校验）。

## 3. 任务字段补齐：让“任务能驱动实现”，而不是“描述性文档”

对任何准备开始的任务，优先补齐以下字段（不补齐就先别写代码）：

- `layer`：仅允许 `docs|core|adapter|ci`（以项目脚本校验口径为准）。
- `adr_refs`：至少 1 个 Accepted ADR；涉及事件契约建议包含 `ADR-0004`。
- `chapter_refs`：至少 1 个 Base 章节（例如 CH01/CH04/CH05/CH06/CH07/CH10）。
- `overlay_refs`：建议固定包含：
  - `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
  - 该任务对应的纵切页（例如 `08-feature-slice-t2-monopoly-loop.md` 或 `08-t5x-*.md`）
- `acceptance[]`：2–6 条（行为/不变式/失败语义至少覆盖 2 类），每条以 `Refs:` 结尾。
- `test_refs[]`：包含 acceptance `Refs:` 的并集；避免“Refs 指向了，但 test_refs 没收录”的证据链断裂。

## 4. 先红灯，再绿灯，再重构（证据链优先）

推荐按 `docs/workflows/task-semantics-gates-evolution.md` 的顺序执行：

1) 红灯：从 `acceptance[]` 的 `Refs:` 生成或补齐测试文件，并写入 `ACC:T<id>.<n>` anchors  
2) 绿灯：只实现让测试变绿的最小代码  
3) 重构：命名/回链/契约一致性/覆盖率门禁  
4) 确定性门禁：`acceptance_check.py`  
5) 软审查：`llm_review.py`（注入确定性证据，降低跑偏概率）

## 5. Windows 本地可玩验证（最小）

建议用 Godot Console 版本启动，便于看到运行日志：

- `C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe --path .`

调试/取证：

- 运行与门禁输出统一落 `logs/`（见 `AGENTS.md` 6.3）。

## 6. 推荐的确定性校验（开始写代码前 / 提交前）

- 回链与结构：`py -3 scripts/python/task_links_validate.py`
- 任务视图一致性审计：`py -3 scripts/python/audit_task_ref_integrity.py`
- 文档编码/疑似乱码扫描：`py -3 scripts/ci/check_encoding_issues.py`

