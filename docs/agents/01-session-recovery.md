# Session Recovery

Use this file after a context reset.

Preferred command: `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`.

## Recovery Order
1. Read `AGENTS.md`.
2. Read [00-index.md](00-index.md).
3. Read [02-repo-map.md](02-repo-map.md).
4. Read the newest files in `execution-plans/` and `decision-logs/`.
5. Read `git log --oneline --decorate -n 10`.
6. If a local review pipeline was running, open `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json`.
7. Read `reason`, `run_type`, `reuse_mode`, and `diagnostics` in `latest.json` first; pay special attention to `artifact_integrity`, `rerun_guard`, `reuse_decision`, `acceptance_preflight`, `llm_timeout_memory`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, and repeated-failure signals surfaced later as `recent_failure_summary`.
8. Treat `logs/ci/active-tasks/task-<id>.active.md` as the shortest recovery pointer when it exists; it now summarizes `Chapter6 blocked by` for `artifact_integrity`, `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, and `recent_failure_summary`.
9. If `active-task`, `resume-task`, or the project-health dashboard also exposes `recommended_action_why` / `Chapter6 stop-loss note`, read that before choosing between reopen, narrow closure, or stop-loss.
10. From that latest index, open `summary.json`, `execution-context.json`, and `repair-guide.md`.
11. If `agent_review_json_path` or `agent_review_md_path` exists in `latest.json`, read that next before rerunning anything.
12. Do not use `run_review_pipeline.py --dry-run` as a recovery pointer producer: dry-run still writes local artifacts in its own `out_dir`, but it no longer publishes `latest.json` or `active-task` sidecars.
13. If `inspect_run.py --kind pipeline --task-id <id>` resolves a newer dry-run pointer, it now skips that candidate automatically and falls back to the newest real recoverable run.
14. If `active-task` and `latest.json` disagree about the active bundle, trust `latest.json` first; `active-task` now follows that bundle on the next refresh.
15. If `active-task` or `inspect_run` surfaces `artifact_integrity`, do not pay for another blind rerun until you confirm whether the producer bundle is stale, incomplete, missing `run_completed`, or only a `planned-only` terminal bundle.

## What To Trust First
- `decision-logs/`: architecture and workflow decisions already made.
- `execution-plans/`: the current plan, stop-loss, and next step.
- `summary.json`: the exact pipeline result.
- `latest.json`: the fastest pointer for deciding whether to resume `6.7`, switch to `6.8`, or stop because rerun guard already triggered.
- `execution-context.json`: git branch, head, recent log, and recovery pointers.
- `repair-guide.json` and `repair-guide.md`: deterministic next actions after a failed pipeline step.
- `agent-review.json` and `agent-review.md`: normalized reviewer verdict built from the producer artifacts.

## Minimum Recovery Questions
- What task or branch is active now?
- Did `latest.json` already say this is `deterministic_ok_llm_not_clean`, so the next move should be `6.8` instead of reopening a full `6.7`?
- Did `latest.json.diagnostics.rerun_guard` already block another full rerun?
- Did `latest.json.diagnostics.llm_retry_stop_loss` already prove that deterministic was green and only the first long LLM wait timed out?
- Did `latest.json.diagnostics.sc_test_retry_stop_loss` already prove the run should stop retrying the same known unit failure?
- Did `latest.json.diagnostics.reuse_decision` or `reuse_mode` already show that deterministic artifacts can be reused?
- Did `active-task` already classify the block as `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `waste_signals`, or `recent_failure_summary`?
- Did the latest recoverable bundle actually complete, or did `artifact_integrity` already tell you the pointer is stale/incomplete?
- Did recovery already show `run_type = planned-only` or `reason = planned_only_incomplete`, meaning the bundle is evidence-only and must not be used to reopen `6.7` or `6.8`?
- Did `Chapter6 blocked by = artifact_integrity` already tell you to fall back to the previous real producer bundle before any rerun choice?
- Did `recommended_action_why`, `Chapter6 stop-loss note`, or `recommended_action = needs-fix-fast` already tell you that a targeted closure is cheaper than another full `6.7`?
- What was the last failing step?
- Was the failure in `sc-test`, `sc-acceptance-check`, or `sc-llm-review`?
- Did `agent-review.json` already classify the outcome as `pass`, `needs-fix`, or `block`?
- Is there an active execution plan that should be resumed instead of replaced?
- Did a decision log already lock the expected behavior?
