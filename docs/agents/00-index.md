# Agents Docs Index

Purpose: keep [AGENTS.md](../../AGENTS.md) short and move durable guidance here.

## Read Order After Context Reset

1. [01-session-recovery.md](01-session-recovery.md)
2. [13-rag-sources-and-session-ssot.md](13-rag-sources-and-session-ssot.md)
3. [02-repo-map.md](02-repo-map.md)
4. [14-startup-stack-and-template-structure.md](14-startup-stack-and-template-structure.md)
5. [03-persistent-harness.md](03-persistent-harness.md)
6. [../workflows/run-protocol.md](../workflows/run-protocol.md)
7. [07-agent-to-agent-review.md](07-agent-to-agent-review.md)
8. First run `py -3 scripts/python/dev_cli.py resume-task --task-id <id>` for the canonical recovery summary
9. If a task-scoped run already exists and the summary still needs a shorter human pointer, read `logs/ci/active-tasks/task-<id>.active.md`
10. Newest files in `execution-plans/` and `decision-logs/`
11. `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json` only when the recovery summary still needs deeper inspection

Recovery shortcut:
- `resume-task` and `inspect_run.py --kind pipeline` now expose `latest_summary_signals` and `chapter6_hints`; use those fields before deciding whether to reopen `6.7` or narrow to `6.8`.
- Recovery decisions now require reading `reason`, `run_type`, `reuse_mode`, and `artifact_integrity` together before trusting the newest pointer.
- `active-task` now also classifies `Chapter6 blocked by` for `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, and `artifact_integrity`, but it should be read after `resume-task`, not before the canonical recovery summary.
- If recovery shows `run_type = planned-only`, `reason = planned_only_incomplete`, or `Chapter6 blocked by = artifact_integrity`, treat that bundle as evidence only; do not reopen `6.7` or `6.8` from it.
- `run_review_pipeline.py --dry-run` no longer publishes `latest.json` or `active-task` sidecars, and `inspect_run.py` automatically skips dry-run-only latest candidates when resolving the next real recovery pointer.
- `active-task` now follows the real bundle pointed to by `latest.json`; when `out_dir` and `latest.json` disagree, trust `latest.json` first.
- If recovery also exposes `recommended_action_why`, read it before choosing between reopen, narrow closure, or stop-loss; `recommended_action = needs-fix-fast` means targeted closure is cheaper than another full rerun.

## Chapter 6 Fast-Ship Card

Use this when you need the cheapest safe daily loop for a single task. Full details live in [workflow.md](../../workflow.md).

1. `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
2. `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft`
3. `6.4 -> 6.5 -> 6.6` in order, keeping the first red run as light as possible
4. `6.5` hard-requires the latest clean `6.4 red-first` summary, and `6.6` hard-requires the latest clean `6.5 green` summary.
5. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
6. Before rerunning `6.7` or `6.8`, read `summary.json`, `latest.json`, `repair-guide.md`, `run-events.jsonl`, and the child step summaries first
7. Check `reason`, `run_type`, `reuse_mode`, `artifact_integrity`, and `diagnostics` in `latest.json` or `summary.json` first; pay attention to `rerun_guard`, `reuse_decision`, `acceptance_preflight`, `llm_timeout_memory`, and stop-loss signals.
8. Read `Chapter6 next action`, `Chapter6 can skip 6.7`, `Chapter6 can go to 6.8`, and `Chapter6 blocked by` before paying for another full rerun.
9. Treat `Chapter6 blocked by=rerun_guard` as a stop-loss signal, `llm_retry_stop_loss` as a narrow LLM-only follow-up, `sc_test_retry_stop_loss` as a known-unit-root-cause stop marker, `waste_signals` as a hint that you should stop paying engine-lane cost before fixing the unit/root cause failure, and `artifact_integrity` as a signal to trust the last real bundle before any rerun choice.
10. If recovery shows `run_type = planned-only` or `reason = planned_only_incomplete`, treat the bundle as a `planned-only terminal bundle`; read evidence from it, but do not reopen `6.7` or `6.8` from it.
11. Only run `6.8` when the current edits directly hit the previous reviewer anchors.
12. If deterministic already passed and only `sc-llm-review` failed, prefer the narrow path that reuses deterministic and reruns only LLM; do not reopen a full `6.7` unless you explicitly need `--allow-full-rerun`.
13. Task semantics edits are not true docs-only clean reuse; they may reuse `sc-test`, but should still rerun `acceptance_check`.
14. If the latest two `6.7` runs stopped at the same `sc-test` failure fingerprint, fix the root cause before retrying; only override this with `--allow-repeat-deterministic-failures`.
15. Fresh `6.7` runs inherit the latest same-task `delivery/security profile` lock; only switch profiles with explicit `--reselect-profile`.
16. If `sc-test` fails twice in the same run, stop resuming and fix the root cause before starting a new run.
17. Use targeted reviewers in `6.8`: code -> `code-reviewer`, semantics / acceptance / overlay -> `semantic-equivalence-auditor`, security -> `security-auditor`.
18. If two `6.8` rounds return the same `Needs Fix` category, severity, and anchors, stop and record instead of paying for a third similar rerun.
19. Treat `status=ok` as clean only when the child `sc-llm-review` summary has no `Needs Fix`, no `Unknown`, and no timeout; if a round shows `failure_kind = timeout-no-summary`, treat it as observation gap, not clean.

## By Topic
- Project overview, startup, stack, and legacy AGENTS background sections:
  - [14-startup-stack-and-template-structure.md](14-startup-stack-and-template-structure.md)
  - [08-project-basics.md](08-project-basics.md)
  - [../../README.md](../../README.md)
  - [../PROJECT_DOCUMENTATION_INDEX.md](../PROJECT_DOCUMENTATION_INDEX.md)
- Harness, recovery, and review handoff:
  - [13-rag-sources-and-session-ssot.md](13-rag-sources-and-session-ssot.md)
  - [01-session-recovery.md](01-session-recovery.md)
  - [03-persistent-harness.md](03-persistent-harness.md)
  - [../workflows/run-protocol.md](../workflows/run-protocol.md)
  - [../workflows/harness-boundary-matrix.md](../workflows/harness-boundary-matrix.md)
  - [07-agent-to-agent-review.md](07-agent-to-agent-review.md)
- Closed-loop testing, quality gates, and Definition of Done:
  - [15-security-release-health-and-runtime-ops.md](15-security-release-health-and-runtime-ops.md)
  - [04-closed-loop-testing.md](04-closed-loop-testing.md)
  - [09-quality-gates-and-done.md](09-quality-gates-and-done.md)
  - [../testing-framework.md](../testing-framework.md)
- Architecture, ADRs, and template rules:
  - [05-architecture-guardrails.md](05-architecture-guardrails.md)
  - [10-template-customization.md](10-template-customization.md)
  - [16-directory-responsibilities.md](16-directory-responsibilities.md)
  - [../workflows/template-bootstrap-checklist.md](../workflows/template-bootstrap-checklist.md)
  - [../workflows/template-upgrade-protocol.md](../workflows/template-upgrade-protocol.md)
  - [../workflows/prototype-lane.md](../workflows/prototype-lane.md)
  - [../architecture/ADR_INDEX_GODOT.md](../architecture/ADR_INDEX_GODOT.md)
- AGENTS maintenance and information architecture:
  - [11-agents-construction-principles.md](11-agents-construction-principles.md)
  - [13-rag-sources-and-session-ssot.md](13-rag-sources-and-session-ssot.md)
- Execution discipline, implementation stop-loss, and script-size guardrails:
  - [12-execution-rules.md](12-execution-rules.md)

## Repository State Files
- `execution-plans/` stores current execution intent and checkpoints.
- `decision-logs/` stores decisions that changed architecture, workflow, or guardrails.
- Unresolved `Needs Fix` must be recorded in `decision-logs/` first, then linked from `execution-plans/` with concrete next-step commands and evidence paths.
- `logs/ci/active-tasks/task-<id>.active.md` is the shortest task-scoped recovery pointer.
- `py -3 scripts/python/dev_cli.py resume-task --task-id <id>` is the preferred full recovery entry because it summarizes the latest run plus matching `execution-plans/` and `decision-logs/`.
- `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json` points to the latest local pipeline artifacts, including `summary.json`, `execution-context.json`, `repair-guide.*`, and `agent-review.*` when generated.
