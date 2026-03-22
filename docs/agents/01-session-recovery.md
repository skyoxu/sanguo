# Session Recovery

Use this file after a context reset.

## Recovery Order
1. Read `AGENTS.md`.
2. Read [00-index.md](00-index.md).
3. Read [02-repo-map.md](02-repo-map.md).
4. Read the newest files in `execution-plans/` and `decision-logs/`.
5. Read `git log --oneline --decorate -n 10`.
6. If a local review pipeline was running, open `logs/ci/<date>/sc-review-pipeline-task-<task>/latest.json`.
7. From that latest index, open `summary.json`, `execution-context.json`, and `repair-guide.md`.
8. If `agent_review_json_path` or `agent_review_md_path` exists in `latest.json`, read that next before rerunning anything.

## What To Trust First
- `decision-logs/`: architecture and workflow decisions already made.
- `execution-plans/`: the current plan, stop-loss, and next step.
- `summary.json`: the exact pipeline result.
- `execution-context.json`: git branch, head, recent log, and recovery pointers.
- `repair-guide.json` and `repair-guide.md`: deterministic next actions after a failed pipeline step.
- `agent-review.json` and `agent-review.md`: normalized reviewer verdict built from the producer artifacts.

## Minimum Recovery Questions
- What task or branch is active now?
- What was the last failing step?
- Was the failure in `sc-test`, `sc-acceptance-check`, or `sc-llm-review`?
- Did `agent-review.json` already classify the outcome as `pass`, `needs-fix`, or `block`?
- Is there an active execution plan that should be resumed instead of replaced?
- Did a decision log already lock the expected behavior?
