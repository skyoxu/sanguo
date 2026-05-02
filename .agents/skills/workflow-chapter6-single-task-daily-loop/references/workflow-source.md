# Workflow Source Summary: Chapter 6

Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.

- Canonical English name: Phase 4: Single Task Daily Loop
- Source line span: 470-1135
- Heading count: 20
- Command-like line count: 75
- Artifact/reference line count: 22

## Headings

- 6. Phase 4: Single Task Daily Loop
- 6.0 Choose the Chapter 6 entrypoint first
- 6.1 Recover state first
- quick recommendation-only read
- quick recommendation-only read
- 6.2 Create recovery documents only when useful
- 6.3 TDD preflight decision
- 6.3 TDD preflight decision
- 6.3 TDD preflight decision
- 6.3 TDD preflight decision
- 6.3 TDD preflight decision
- 6.4 Red stage
- 6.5 Green stage
- 6.6 Refactor stage
- 6.7 Unified task-level review pipeline
- 6.8 Clean up Needs Fix
- 6.9 Repository-level validation before commit
- 6.1 Recover state first
- 6.1 Recover state first
- quick recommendation-only read

## Command And Artifact Signals

- `py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
- `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
- `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only`
- `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <id>`
- `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <id> --recommendation-only`
- `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --out-json logs/ci/<date>/resume-task-<id>.json --out-md logs/ci/<date>/resume-task-<id>.md`
- `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <id> --out-json logs/ci/<date>/inspect-pipeline-<id>.json`
- `py -3 scripts/python/dev_cli.py new-execution-plan --title "<topic>" --task-id <id>`
- `py -3 scripts/python/dev_cli.py new-decision-log --title "<topic>" --task-id <id>`
- `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft`
- `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit`
- `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit --include-prd-context --prd-context-path .taskmaster/docs/prd.txt`
- `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"`
- `py -3 scripts/sc/build.py tdd --task-id <id> --stage green`
- `py -3 scripts/sc/build.py tdd --task-id <id> --stage green --allow-contract-changes`
- `py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile standard`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea`
- `-  `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only`  recovery  `preferred_lane = run-6.7 | run-6.8 | fix-deterministic | repo-noise-stop | record-residual | inspect-first` 6.7`
- `- `run_review_pipeline.py` now consumes the same route signal before a fresh full rerun. If recovery already routes to `inspect-first`, `repo-noise-stop`, `fix-deterministic`, or `run-6.8`, the script stops before refact`
- `- When the latest run is already `sc-test = ok + sc-acceptance-check = ok + sc-llm-review != clean` and this round did not touch deterministic files, do not reopen a full 6.7 by default; prefer 6.8 or `py -3 scripts/sc/l`
- `- `run_review_pipeline.py`  `DELIVERY_PROFILE``
- `-  6.7  reviewer  `rc=124``py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-timeout-sec 900``
- `- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile <profile> --allow-full-unit-fallback``
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --dry-run --skip-test --skip-acceptance --skip-agent-review`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --max-wall-time-sec 7200`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --resume`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --fork`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --abort`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --force-new-run-id`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --run-id <run_id> --allow-overwrite --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --skip-llm-review`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-semantic-gate require --llm-agent-timeout-sec 300 --context-refresh-after-failures 2 --context-refres`
- `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-diff-mode summary --context-refresh-after-diff-lines 400 --context-refresh-after-diff-categories 4`
- `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile playable-ea`
- `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship`
- `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile standard`
- `- `llm_review_needs_fix_fast.py`  `DELIVERY_PROFILE`  reviewer / diff / timeout`
- `-  6.7  6.8 `fast-ship`  reviewer  `llm_review_needs_fix_fast.py`  6.7 `run_review_pipeline.py`  `minimal / targeted` tier  `code-reviewer + security-auditor` `full`  reviewer  `semantic-equivalence-auditor``
