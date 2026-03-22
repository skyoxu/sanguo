# Execution Plans

Store durable execution progress here.

Rules:
- one file per active initiative or focused branch
- update checkpoints instead of rewriting history in chat only
- include `Branch`, `Git Head`, `Goal`, `Current step`, `Stop-loss`, and `Next action`
- use `Related decision logs` as the durable decision-link set for recovery
- include `Recovery command`, `Open questions`, and `Exit criteria` so a later agent can resume without chat history
- include `Related task id(s)`, `Related run id`, and `Related latest.json` when a pipeline run exists
- if a historical item has no preserved task id or run id, write `n/a` and the reason explicitly
- keep high-frequency runtime noise in `logs/`, not here
- validate changes with `py -3 scripts/python/validate_recovery_docs.py --dir execution-plans`
- create a new scaffold with `py -3 scripts/python/new_execution_plan.py --title "<title>" [--task-id <id>]`

