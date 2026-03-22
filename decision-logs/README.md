# Decision Logs

Store durable decisions here.

Use a new file when a decision changes:
- architecture direction
- guardrail hardness
- workflow contract
- recovery model
- release policy

Rules:
- include `Branch` and `Git Head` for the decision context
- include `Why now`, `Recovery impact`, and `Validation` so the decision stays actionable after a context reset
- include `Supersedes` / `Superseded by` explicitly, even when the value is `none`
- include `Related task id(s)`, `Related run id`, and `Related latest.json` when the decision was verified by pipeline artifacts
- if a historical decision predates stable task id or run id capture, write `n/a` and the reason explicitly
- validate changes with `py -3 scripts/python/validate_recovery_docs.py --dir decision-logs`
- create a new scaffold with `py -3 scripts/python/new_decision_log.py --title "<title>" [--task-id <id>]`

