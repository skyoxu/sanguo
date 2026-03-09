# DELIVERY_PROFILE (Fixed Fast Mode)

## Scope

This repository is now fixed to a single delivery posture equivalent to `fast-ship`.
No runtime profile switching is supported in this project.

## Effective Defaults

- Security profile default: `host-safe`
- Build posture: `warn_as_error = true`
- Unit coverage gate defaults: `lines >= 70`, `branches >= 60`
- Acceptance defaults:
  - `strict_adr_status = false`
  - `require_task_test_refs = true`
  - `require_executed_refs = false`
  - `require_headless_e2e = false`
  - `subtasks_coverage = warn`
- LLM review defaults:
  - `semantic_gate = warn`
  - `strict = false`
- CI task links warning budget: `200`

## Implementation Notes

- This repository intentionally does not expose `playable-ea` / `standard` switches.
- If stricter checks are needed, pass explicit CLI flags in one-off runs.
- Team default remains optimized for fast integration with baseline quality controls.
