# Workflows Documentation Index

This file indexes the current `docs/workflows/` root documents and records how translation files and subdirectories are handled.

## Scope Rules

- The primary document table includes only root-level `docs/workflows/*.md` primary documents.
- Translation and Chinese-specific files (`.cn.md`, `.zh-CN.md`, `-zh.md`) are listed in a separate table.
- Machine-readable config, command whitelist files, and temporary check artifacts are listed as support files.
- `examples/` and `templates/` are summarized by directory responsibility instead of expanded file by file.
- `README.md` is not included in the primary document table.

## Classification Rules

- The unfinished-work column only records explicit planning, evolution, or ongoing governance content.
- Created and modified timestamps come from the current Windows filesystem metadata.
- Rule, SOP, index, reference, and template documents are marked as having no explicit unfinished work unless they state follow-up work.
- Translation files without a matching English primary document are treated as independent Chinese-specific documents.

## Primary Root Documents

| File | Created | Modified | Main Content | Unfinished Work |
| --- | --- | --- | --- | --- |
| `acceptance-check-and-llm-review.md` | `2025-12-20 18:03:39` | `2026-02-22 16:29:51` | Acceptance gate and optional LLM review responsibilities, usage, and stop-loss boundaries. | No explicit unfinished work. |
| `acceptance-semantics-methodology.md` | `2026-01-07 12:12:59` | `2026-02-22 16:29:51` | Acceptance semantics governance: obligations, refs, anchors, evidence chains, and weak-clause rules. | No explicit unfinished work. |
| `build_taskmaster_tasks.md` | `2025-12-20 01:00:55` | `2025-12-20 19:24:44` | Taskmaster task construction, dependency closure, and tag handling. | No explicit unfinished work. |
| `business-repo-upgrade-guide.md` | `2026-03-22 21:37:48` | `2026-05-01 13:53:30` | Business-repo migration guide for recovery, gates, workflow scripts, docs, dependencies, and Chapter 7 profile migration. | Ongoing maintenance required. |
| `chapter-6-t56-optimization-guide.md` | `2026-03-31 22:43:27` | `2026-04-13 00:38:16` | Chapter 6 T56 optimization notes, real log signals, upgrade method, and execution posture. | No explicit unfinished work. |
| `chapter7-profile-guide.md` | `2026-04-30 14:30:26` | `2026-04-30 21:19:28` | Chapter 7 profile load order, field semantics, seed templates, minimal overrides, and validation commands. | Ongoing maintenance required. |
| `cloud-platform-evolution-plan.md` | `2026-04-15 13:40:38` | `2026-04-25 14:47:28` | Roadmap from local harness to cloud control plane, cloud workspace, and Windows execution plane. | Ongoing maintenance required. |
| `cloud-user-telemetry-and-feedback-plan.md` | `2026-04-20 20:53:50` | `2026-04-20 21:50:04` | Future cloud telemetry plan for workflow optimization, replay, stop-loss, and product evolution. | Ongoing maintenance required. |
| `contracts-catalog-guide.md` | `2026-01-14 00:43:59` | `2026-01-14 16:27:43` | Contracts catalog generation, artifact rules, and version-control policy. | No explicit unfinished work. |
| `contracts-template-v1.md` | `2026-02-28 12:07:36` | `2026-02-28 16:29:04` | Contract authoring template, hard rules, workflow, and minimal validation commands. | No explicit unfinished work. |
| `doc-stack-convergence-guide.md` | `2025-12-17 11:58:50` | `2025-12-17 11:58:50` | Documentation convergence workflow for mojibake scans, old terminology, and base/migration consistency. | No explicit unfinished work. |
| `gate-bundle.md` | `2026-03-08 20:35:19` | `2026-05-01 13:53:30` | Gate bundle purpose, command entrypoints, gate groups, CI integration, and Chapter 7 gate coverage. | Ongoing maintenance required. |
| `GM-NG-T2-playable-guide.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | Guide for driving the first T2 playable slice from GM/NG tasks and PRD/Overlay sources. | No explicit unfinished work. |
| `harness-boundary-matrix.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | Boundary matrix for stable harness capabilities and business-repo customization zones. | Ongoing maintenance required. |
| `hermes-openai-api-and-orchestration-optimization-plan.md` | `2026-04-13 00:38:17` | `2026-04-13 00:38:17` | Hermes/OpenAI API migration ideas and Chapter 5/6 orchestration optimization plan. | Ongoing maintenance required. |
| `local-hard-checks.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | Repository-level local hard-check entrypoints, use cases, commands, and result reading. | No explicit unfinished work. |
| `openspec-vs-current-stack.md` | `2026-04-25 22:32:41` | `2026-04-25 22:36:10` | Comparison between OpenSpec and the current stack, with reusable ideas and non-goals. | Ongoing maintenance required. |
| `overlay-generation-quickstart.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | Quickstart for overlay generation commands and the minimal workflow. | No explicit unfinished work. |
| `overlay-generation-sop.md` | `2026-03-22 21:37:48` | `2026-03-22 21:37:48` | Overlay generation SOP: entry selection, required inputs, page profile, and stop-loss rules. | No explicit unfinished work. |
| `overlays-authoring-guide.md` | `2026-01-13 22:20:06` | `2026-03-22 21:37:48` | Overlay directory structure, front matter, chapter 08 writing boundaries, and maintenance constraints. | No explicit unfinished work. |
| `project-health-dashboard.md` | `2026-03-24 23:17:15` | `2026-04-13 00:38:17` | Project health dashboard commands, outputs, page location, and recommended usage. | Ongoing maintenance required. |
| `prototype-lane-playbook.md` | `2026-04-13 00:38:17` | `2026-04-20 14:00:33` | End-to-end prototype lane playbook from prototype record to red/green/refactor closure. | No explicit unfinished work. |
| `prototype-lane.md` | `2026-03-24 14:08:37` | `2026-04-20 14:00:33` | Prototype lane positioning, differences from EA/formal delivery, relaxed rules, and required artifacts. | Ongoing maintenance required. |
| `prototype-tdd.md` | `2026-04-13 00:38:17` | `2026-04-21 14:14:00` | Prototype TDD entrypoints, stage differences, parameters, and boundary with formal Chapter 6 TDD. | No explicit unfinished work. |
| `run-protocol.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | Harness run protocol, artifact layout, sidecar contract, recovery consumption order, and consumer duties. | Ongoing maintenance required. |
| `script-entrypoints-index.md` | `2026-03-25 01:58:41` | `2026-04-30 21:32:44` | Index of workflow-facing scripts, parameters, prerequisites, behavior, and excluded one-off utilities. | Ongoing maintenance required. |
| `serena-mcp-command-reference.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | Serena MCP command reference and context-gathering patterns. | No explicit unfinished work. |
| `stable-public-entrypoints.md` | `2026-03-25 10:59:04` | `2026-04-30 21:32:44` | Stable public workflow entrypoints, usage scenarios, and selection rules. | Ongoing maintenance required. |
| `superclaude-command-reference.md` | `2025-12-07 16:47:04` | `2025-12-17 11:58:50` | SuperClaude command reference, common calls, and task-analysis patterns. | No explicit unfinished work. |
| `superpowers-vs-chapter6-router.md` | `2026-04-25 23:19:25` | `2026-04-25 23:23:49` | Comparison between Superpowers and this repo Chapter 6 router, with useful ideas and non-goals. | Ongoing maintenance required. |
| `task-master-superclaude-integration.md` | `2025-12-07 16:47:04` | `2026-01-14 16:27:43` | Task Master and SuperClaude collaboration model, responsibility split, and task lifecycle. | No explicit unfinished work. |
| `task-semantics-gates-evolution.md` | `2025-12-25 15:28:42` | `2026-02-22 16:29:51` | Task semantics gates, test evidence chain, script index, and current governance posture. | Ongoing maintenance required. |
| `template-bootstrap-checklist.md` | `2026-03-22 21:37:48` | `2026-04-13 00:38:17` | Checklist for turning the template repo into a new project: identity, profiles, security, and task sources. | No explicit unfinished work. |
| `template-upgrade-protocol.md` | `2026-03-24 14:08:37` | `2026-05-01 13:53:30` | Business-repo template upgrade protocol, including Chapter 7 profile bundle migration rules. | Ongoing maintenance required. |
| `workflow-rule-feedback-protocol.md` | `2026-04-19 18:13:55` | `2026-04-19 18:39:15` | Protocol for business-repo workflow feedback, promotion rules, and required evidence. | Ongoing maintenance required. |

## Support Files

| File | Created | Modified | Purpose | Included In Primary Table |
| --- | --- | --- | --- | --- |
| `_tmp_utf8_test.txt` | `2026-04-28 17:56:30` | `2026-04-28 17:56:30` | Temporary UTF-8 test artifact. | No. Temporary file; keep untracked or remove. |
| `chapter7-profile.json` | `2026-04-30 14:06:44` | `2026-04-30 14:40:02` | Repo-local Chapter 7 UI wiring profile override consumed by scripts. | No. Machine-readable configuration. |
| `unified-pipeline-command-whitelist.txt` | `2026-03-08 20:35:19` | `2026-04-13 00:38:17` | Unified pipeline command whitelist format reference for CI or pre-run checks. | No. Non-Markdown support file. |

## Translation And Chinese Files

| File | Primary Document | Created | Modified | Type | Maintenance Rule |
| --- | --- | --- | --- | --- | --- |
| `cloud-platform-evolution-plan.cn.md` | `cloud-platform-evolution-plan.md` | `2026-04-28 16:57:48` | `2026-04-28 17:04:51` | Chinese translation | Sync after substantive primary-document updates. |
| `cloud-user-telemetry-and-feedback-plan.cn.md` | `cloud-user-telemetry-and-feedback-plan.md` | `2026-04-28 17:23:27` | `2026-04-28 17:23:27` | Chinese translation | Sync after substantive primary-document updates. |
| `prototype-7day-playable-godot-zh.md` | No matching English primary document | `2026-04-15 14:31:27` | `2026-04-21 18:47:54` | Chinese-specific document | Maintain as an independent Chinese-specific document until a matching primary document exists. |
| `prototype-workflow-zh.md` | No matching English primary document | `2026-04-15 13:48:15` | `2026-05-01 13:52:55` | Chinese-specific document | Maintain as an independent Chinese-specific document until a matching primary document exists. |

## Subdirectory Decision

| Subdirectory | Current Content | Expanded In This Index | Maintenance Rule |
| --- | --- | --- | --- |
| `examples/` | Example JSON/HTML/MD outputs, 35 files total, 4 Markdown files. | No. Maintain by directory responsibility. | Update `examples/README.md` and affected examples when output schemas, fields, or recovery reading rules change. |
| `templates/` | Workflow, contract, and Chapter 7 profile templates, 6 files total, 4 Markdown files. | No. Maintain by template family. | Sync templates and referencing docs when contract templates, workflow feedback templates, or Chapter 7 profile fields change. |

## Suggested Reading Order

1. `stable-public-entrypoints.md`
2. `script-entrypoints-index.md`
3. `run-protocol.md`
4. `local-hard-checks.md`
5. `project-health-dashboard.md`
6. `chapter7-profile-guide.md` when working on Chapter 7 UI wiring or profile overrides
7. `prototype-lane.md` / `prototype-tdd.md` / `prototype-lane-playbook.md`
8. `template-upgrade-protocol.md` / `business-repo-upgrade-guide.md`
9. `cloud-platform-evolution-plan.md` / `cloud-user-telemetry-and-feedback-plan.md` / `hermes-openai-api-and-orchestration-optimization-plan.md` when planning platform evolution
