# Workflow Source Summary: Chapter 5

Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.

- Canonical English name: Phase 3: Conditional Semantics Stabilization
- Source line span: 494-682
- Heading count: 7
- Command-like line count: 12
- Artifact/reference line count: 4

## Headings

- 5. Phase 3: Conditional Semantics Stabilization
- 5.1 Single-task lightweight lane
- 5.1 Single-task lightweight lane
- 5.1 Single-task lightweight lane
- 5.1 Single-task lightweight lane
- 5.1 Single-task lightweight lane
- 5.2 Batch instability lane

## Command And Artifact Signals

- ``py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile <profile>`
- `shard `py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start <start> --task-id-end <end> --batch-preset <preset> --delivery-profile <profile>`
- `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship`
- `py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start 101 --task-id-end 180 --batch-preset stable-batch --delivery-profile fast-ship --max-tasks-per-shard 12`
- `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --resume-failed-task-from first-failed-step`
- `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --out-dir logs/ci/<date>/single-task-light-lane-t<id>-fresh --no-resume`
- `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --stop-on-step-failure`
- `py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --max-rewrite-change-ratio 0.35`
- `py -3 scripts/python/run_obligations_jitter_batch5x3.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --escalate-max-runs 3 --max-schema-errors 5 --reuse-last-ok --expl`
- `py -3 scripts/python/run_obligations_freeze_pipeline.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --reuse-last-ok --explain-reuse-miss`
- `py -3 scripts/python/run_obligations_freeze_pipeline.py --skip-jitter --raw logs/ci/<date>/sc-llm-obligations-jitter-batch5x3-raw.json --require-judgable --require-freeze-pass`
- `py -3 scripts/python/run_obligations_freeze_pipeline.py --skip-jitter --raw logs/ci/<date>/sc-llm-obligations-jitter-batch5x3-raw.json --require-judgable --require-freeze-pass --approve-promote`
- ``summary.json`  dashboard`
- `summary.json`
- `merged/summary.json`
- ``summary.json`  batch dashboard`
