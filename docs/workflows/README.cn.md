# Workflows 文档索引

本文档索引当前 `docs/workflows/` 根目录文档，并记录 translation files 与 subdirectories 的处理方式。

## 范围规则

- primary document table 只包含根目录级 `docs/workflows/*.md` primary documents。
- translation 与 Chinese-specific files（`.cn.md`、`.zh-CN.md`、`-zh.md`）列入单独表格。
- machine-readable config、command whitelist files 与 temporary check artifacts 列为 support files。
- `examples/` 与 `templates/` 按目录职责汇总，不逐文件展开。
- `README.md` 不纳入 primary document table。

## 分类规则

- unfinished-work column 只记录明确的 planning、evolution 或 ongoing governance 内容。
- Created 与 Modified timestamp 来自当前 Windows filesystem metadata。
- Rule、SOP、index、reference 与 template documents 如未声明 follow-up work，则标记为无明确未完成项。
- 没有匹配英文 primary document 的 translation files，按独立 Chinese-specific documents 处理。

## 根目录 Primary Documents

| 文件 | 创建时间 | 修改时间 | 主要内容 | 未完成项 |
| --- | --- | --- | --- | --- |
| `acceptance-check-and-llm-review.md` | `2025-12-20 18:03:39` | `2026-02-22 16:29:51` | Acceptance gate 与可选 LLM review 的职责、用法和 stop-loss 边界。 | 无明确未完成项。 |
| `acceptance-semantics-methodology.md` | `2026-01-07 12:12:59` | `2026-02-22 16:29:51` | Acceptance semantics governance：obligations、refs、anchors、evidence chains 与 weak-clause rules。 | 无明确未完成项。 |
| `build_taskmaster_tasks.md` | `2025-12-20 01:00:55` | `2025-12-20 19:24:44` | Taskmaster task construction、dependency closure 与 tag handling。 | 无明确未完成项。 |
| `business-repo-upgrade-guide.md` | `2026-03-22 21:37:48` | `2026-05-01 13:53:30` | Business-repo migration guide，覆盖 recovery、gates、workflow scripts、docs、dependencies 与 Chapter 7 profile migration。 | 需要持续维护。 |
| `chapter-6-t56-optimization-guide.md` | `2026-03-31 22:43:27` | `2026-04-13 00:38:16` | Chapter 6 T56 optimization notes、真实日志信号、升级方法和执行姿态。 | 无明确未完成项。 |
| `chapter7-profile-guide.md` | `2026-04-30 14:30:26` | `2026-04-30 21:19:28` | Chapter 7 profile load order、field semantics、seed templates、minimal overrides 与 validation commands。 | 需要持续维护。 |
| `cloud-platform-evolution-plan.md` | `2026-04-15 13:40:38` | `2026-04-25 14:47:28` | 从 local harness 到 cloud control plane、cloud workspace 与 Windows execution plane 的路线图。 | 需要持续维护。 |
| `cloud-user-telemetry-and-feedback-plan.md` | `2026-04-20 20:53:50` | `2026-04-20 21:50:04` | 面向 workflow optimization、replay、stop-loss 与 product evolution 的未来 cloud telemetry plan。 | 需要持续维护。 |
| `contracts-catalog-guide.md` | `2026-01-14 00:43:59` | `2026-01-14 16:27:43` | Contracts catalog generation、artifact rules 与 version-control policy。 | 无明确未完成项。 |
| `contracts-template-v1.md` | `2026-02-28 12:07:36` | `2026-02-28 16:29:04` | Contract authoring template、hard rules、workflow 与 minimal validation commands。 | 无明确未完成项。 |
| `doc-stack-convergence-guide.md` | `2025-12-17 11:58:50` | `2025-12-17 11:58:50` | Documentation convergence workflow，覆盖 mojibake scans、old terminology 与 base/migration consistency。 | 无明确未完成项。 |
| `gate-bundle.md` | `2026-03-08 20:35:19` | `2026-05-01 13:53:30` | Gate bundle 的目的、command entrypoints、gate groups、CI integration 与 Chapter 7 gate coverage。 | 需要持续维护。 |
| `GM-NG-T2-playable-guide.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | 从 GM/NG tasks 与 PRD/Overlay sources 驱动首个 T2 playable slice 的指南。 | 无明确未完成项。 |
| `harness-boundary-matrix.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | stable harness capabilities 与 business-repo customization zones 的 boundary matrix。 | 需要持续维护。 |
| `hermes-openai-api-and-orchestration-optimization-plan.md` | `2026-04-13 00:38:17` | `2026-04-13 00:38:17` | Hermes/OpenAI API migration ideas 与 Chapter 5/6 orchestration optimization plan。 | 需要持续维护。 |
| `local-hard-checks.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | repository-level local hard-check entrypoints、use cases、commands 与 result reading。 | 无明确未完成项。 |
| `openspec-vs-current-stack.md` | `2026-04-25 22:32:41` | `2026-04-25 22:36:10` | OpenSpec 与当前 stack 的对比，包含 reusable ideas 与 non-goals。 | 需要持续维护。 |
| `overlay-generation-quickstart.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | overlay generation commands 的 quickstart 与 minimal workflow。 | 无明确未完成项。 |
| `overlay-generation-sop.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | Overlay generation SOP：entry selection、required inputs、page profile 与 stop-loss rules。 | 无明确未完成项。 |
| `overlays-authoring-guide.md` | `2026-01-13 22:20:06` | `2026-03-22 21:37:48` | Overlay directory structure、front matter、chapter 08 writing boundaries 与 maintenance constraints。 | 无明确未完成项。 |
| `project-health-dashboard.md` | `2026-03-24 23:17:15` | `2026-04-13 00:38:17` | Project health dashboard commands、outputs、page location 与 recommended usage。 | 需要持续维护。 |
| `prototype-lane-playbook.md` | `2026-04-13 00:38:17` | `2026-04-20 14:00:33` | 从 prototype record 到 red/green/refactor closure 的 end-to-end prototype lane playbook。 | 无明确未完成项。 |
| `prototype-lane.md` | `2026-03-24 14:08:37` | `2026-04-20 14:00:33` | Prototype lane positioning、与 EA/formal delivery 的差异、relaxed rules 与 required artifacts。 | 需要持续维护。 |
| `prototype-tdd.md` | `2026-04-13 00:38:17` | `2026-04-21 14:14:00` | Prototype TDD entrypoints、stage differences、parameters，以及与 formal Chapter 6 TDD 的边界。 | 无明确未完成项。 |
| `run-protocol.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | Harness run protocol、artifact layout、sidecar contract、recovery consumption order 与 consumer duties。 | 需要持续维护。 |
| `script-entrypoints-index.md` | `2026-03-25 01:58:41` | `2026-04-30 21:32:44` | workflow-facing scripts、parameters、prerequisites、behavior 与 excluded one-off utilities 的索引。 | 需要持续维护。 |
| `serena-mcp-command-reference.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | Serena MCP command reference 与 context-gathering patterns。 | 无明确未完成项。 |
| `stable-public-entrypoints.md` | `2026-03-25 10:59:04` | `2026-04-30 21:32:44` | Stable public workflow entrypoints、usage scenarios 与 selection rules。 | 需要持续维护。 |
| `superclaude-command-reference.md` | `2025-12-07 16:47:04` | `2025-12-17 11:58:50` | SuperClaude command reference、common calls 与 task-analysis patterns。 | 无明确未完成项。 |
| `superpowers-vs-chapter6-router.md` | `2026-04-25 23:19:25` | `2026-04-25 23:23:49` | Superpowers 与本仓 Chapter 6 router 的对比，包含 useful ideas 与 non-goals。 | 需要持续维护。 |
| `task-master-superclaude-integration.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | Task Master 与 SuperClaude 的 collaboration model、responsibility split 与 task lifecycle。 | 无明确未完成项。 |
| `task-semantics-gates-evolution.md` | `2025-12-25 15:28:42` | `2026-02-22 16:29:51` | Task semantics gates、test evidence chain、script index 与 current governance posture。 | 需要持续维护。 |
| `template-bootstrap-checklist.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | 将 template repo 转为新项目的 checklist：identity、profiles、security 与 task sources。 | 无明确未完成项。 |
| `template-upgrade-protocol.md` | `2026-03-24 14:08:37` | `2026-05-01 13:53:30` | Business-repo template upgrade protocol，包含 Chapter 7 profile bundle migration rules。 | 需要持续维护。 |
| `workflow-rule-feedback-protocol.md` | `2026-04-19 18:13:55` | `2026-04-19 18:39:15` | business-repo workflow feedback、promotion rules 与 required evidence 的 protocol。 | 需要持续维护。 |

## Support Files

| 文件 | 创建时间 | 修改时间 | 用途 | 是否纳入 Primary Table |
| --- | --- | --- | --- | --- |
| `chapter7-profile.json` | `2026-04-30 14:06:44` | `2026-04-30 14:40:02` | 供 scripts 消费的 repo-local Chapter 7 UI wiring profile override。 | 否。属于 machine-readable configuration。 |
| `unified-pipeline-command-whitelist.txt` | `2026-03-08 20:35:19` | `2026-04-13 00:38:17` | CI 或 pre-run checks 使用的 unified pipeline command whitelist 格式参考。 | 否。属于 non-Markdown support file。 |

## Translation And Chinese Files

| 文件 | Primary Document | 创建时间 | 修改时间 | 类型 | 维护规则 |
| --- | --- | --- | --- | --- | --- |
| `cloud-platform-evolution-plan.cn.md` | `cloud-platform-evolution-plan.md` | `2026-04-28 16:57:48` | `2026-04-28 17:04:51` | Chinese translation | primary document 发生实质更新后同步。 |
| `cloud-user-telemetry-and-feedback-plan.cn.md` | `cloud-user-telemetry-and-feedback-plan.md` | `2026-04-28 17:23:27` | `2026-04-28 17:23:27` | Chinese translation | primary document 发生实质更新后同步。 |
| `prototype-7day-playable-godot-zh.md` | 无匹配英文 primary document | `2026-04-15 14:31:27` | `2026-04-21 18:47:54` | Chinese-specific document | 在出现匹配 primary document 前，作为独立中文专题文档维护。 |
| `prototype-workflow-zh.md` | 无匹配英文 primary document | `2026-04-15 13:48:15` | `2026-05-01 13:52:55` | Chinese-specific document | 在出现匹配 primary document 前，作为独立中文专题文档维护。 |

## Subdirectory Decision

| 子目录 | 当前内容 | 是否在本索引中逐文件展开 | 维护规则 |
| --- | --- | --- | --- |
| `examples/` | Example JSON/HTML/MD outputs，共 35 个文件，其中 4 个 Markdown files。 | 否。按目录职责维护。 | output schemas、fields 或 recovery reading rules 变化时，更新 `examples/README.md` 和受影响 examples。 |
| `templates/` | Workflow、contract 与 Chapter 7 profile templates，共 6 个文件，其中 4 个 Markdown files。 | 否。按 template family 维护。 | contract templates、workflow feedback templates 或 Chapter 7 profile fields 变化时，同步 templates 和引用文档。 |

## Suggested Reading Order

1. `stable-public-entrypoints.md`
2. `script-entrypoints-index.md`
3. `run-protocol.md`
4. `local-hard-checks.md`
5. `project-health-dashboard.md`
6. 处理 Chapter 7 UI wiring 或 profile overrides 时阅读 `chapter7-profile-guide.md`
7. `prototype-lane.md` / `prototype-tdd.md` / `prototype-lane-playbook.md`
8. `template-upgrade-protocol.md` / `business-repo-upgrade-guide.md`
9. 做 platform evolution 规划时阅读 `cloud-platform-evolution-plan.md` / `cloud-user-telemetry-and-feedback-plan.md` / `hermes-openai-api-and-orchestration-optimization-plan.md`

## 任务三联生成

当需要用确定性的 task triplet generation 替代 Taskmaster MCP 直接生成时，使用这些脚本：

- `scripts/python/extract_requirement_anchors.py` - 使用 `--prd-path`、`--gdd-path`、`--epics-path`、`--stories-path` 与 `--source-glob`，从可配置 PRD/GDD/epics/stories/overlay/ADR sources 提取 requirement anchors。
- `scripts/python/generate_task_candidates_from_sources.py` - 从 requirement anchors 创建 normalized task candidates。
- `scripts/python/enrich_task_candidates.py` - 使用 repository ADR、overlay、contract-event、test、existing-task、owner/layer、acceptance、evidence-ref 与 duplicate-candidate evidence 富化 candidates。
- `scripts/python/audit_task_candidate_coverage.py` - 在 triplet compilation 前阻断 P0/P1 omissions。
- `scripts/python/compile_task_triplet.py` - 写入 task-triplet patch，或通过 `--write` 更新 task view files。

最终 `tasks.json` 仍然由 `scripts/python/build_taskmaster_tasks.py` 从 `tasks_back.json` 与 `tasks_gameplay.json` 生成。
