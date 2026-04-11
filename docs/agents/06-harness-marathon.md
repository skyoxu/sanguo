# Harness Marathon

Current policy:
- automatic step retry inside one invocation via `--max-step-retries <n>`
- per-run wall-time stop-loss via `--max-wall-time-sec <sec>`
- checkpoint after each persisted step via `marathon-state.json`
- append-only timeline via `run-events.jsonl`, now with stable taxonomy fields (`turn_id`, `item_kind`, `item_id`, `event_family`) so a recovering agent can read exact run transitions without scraping terminal logs
- capability discovery via `harness-capabilities.json`, so an external harness can check supported recovery actions before issuing follow-up commands
- soft approval sidecar via `approval-request.json` / `approval-response.json` for fork-oriented recovery; the pipeline records the request automatically when fork becomes the isolated recovery path, and recovery consumers now treat `pending|approved|denied|invalid|mismatched` as real pause/resume/fork routing states instead of soft hints only
- explicit `--resume` to continue the latest matching task run
- explicit `--abort` to freeze the latest matching task run without executing more steps
- explicit `--fork` to keep the original run immutable and continue in a new run id
- deterministic `context_refresh_needed` heuristics based on repeated failures, repeated resumes, diff growth, and cross-category drift
- deterministic agent-review linkage: isolated reviewer findings stay on `resume`, single `medium` structural drift stays on `resume`, cross-step `needs-fix` or high-severity structural drift upgrades to `refresh`, and integrity breaks (`artifact-integrity` high, `summary-integrity`, `schema-integrity`) upgrade to `fork`
- `repair-guide.json/md` emits deterministic `--resume` / `--fork` guidance when recovery is needed, and folds the latest soft approval decision back into the human-readable recovery steps

Current operator flow:
1. Run `py -3 scripts/sc/run_review_pipeline.py --task-id <id> ...` normally.
2. If a step fails and you want one in-process retry budget, set `--max-step-retries <n>`.
3. If the run should be bounded, set `--max-wall-time-sec <sec>`.
4. Before resuming after a context reset or long pause, run `py -3 scripts/python/dev_cli.py resume-task --task-id <id>` to summarize the latest task run and matched recovery docs.
5. Fix the first blocking issue from `repair-guide.md`.
6. Read `run-events.jsonl` first if you need to understand where the run actually stopped.
7. Resume the same artifact set with `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --resume`.
8. If you want a clean recovery branch, use `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --fork`.
9. If the run should be stopped permanently, mark it with `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --abort`.

Current heuristics:
- `--context-refresh-after-failures <n>`: when one step fails this many times, mark `context_refresh_needed=true`
- `--context-refresh-after-resumes <n>`: when resume count reaches this value, mark `context_refresh_needed=true`
- `--context-refresh-after-diff-lines <n>`: when working-tree diff grows by this many lines from the run baseline, mark `context_refresh_needed=true`
- `--context-refresh-after-diff-categories <n>`: when newly added diff categories from the run baseline reach this count, mark `context_refresh_needed=true`
- deterministic semantic-mix signal: when the current diff spans both `governance` and `implementation` axes and the run adds new semantic axes, mark `context_refresh_needed=true`
- deterministic reviewer semantic-mix signal: if agent review spans both implementation-owned and governance-owned steps, preserve a refresh reason even when the producer pipeline itself stayed green
- the refresh signal is advisory but deterministic; it lands in `marathon-state.json`, `execution-context.json`, and `repair-guide.json/md`
- diff growth/complexity is computed from Git-visible workspace changes (`git diff --numstat HEAD`, changed file paths, and untracked files), not from full file rescans

Category model (template-friendly):
- governance: `docs/`, `.github/`, `.taskmaster/`, `execution-plans/`, `decision-logs/`, root guidance files
- implementation: `scripts/`, `Game.Core/`, `Game.Godot/`, `Scenes/`, `Assets/`, solution/project files
- contracts: `Game.Core/Contracts/`
- tests: `Game.Core.Tests/`, `Tests.Godot/`, `Game.Godot.Tests/`

Not implemented yet:
- semantic-drift heuristics beyond directory/category proxies and reviewer owner-step/category analysis
- full approval contract scheduling beyond the current `resume` / `fork` hard blocks
- full fork graph visualization or scheduler-style marathon orchestration
