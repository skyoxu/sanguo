# task-193-tiles-ids-add-mapping-completion-plan

- Title: Implement part 6 tiles ids add mapping completion
- Status: active
- Branch: task/T193
- Git Head: 7257d294ccac563009b4a147ae0ded84a0443c29
- Goal: Close Task 193 tile-id mapping completion with deterministic core validation and Godot boundary evidence.
- Scope: Task 193 acceptance, tests, runtime boundary, and Chapter 6/6.9 validation artifacts.
- Current step: Rerun local hard checks after refreshing overlay drift and recovery docs.
- Last completed step: Task 193 xUnit, sc-test, acceptance check, and semantic-equivalence-auditor narrow review passed.
- Stop-loss: Do not run the forbidden full `py -3 scripts/sc/run_review_pipeline.py --task-id 193`; use recovery routing and narrow reviewer evidence.
- Next action: `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`
- Recovery command: `py -3 scripts/python/dev_cli.py resume-task --task-id 193`
- Open questions: none
- Exit criteria: Local hard checks pass and Task 193 has no P0/P1 Needs Fix under fast-ship evidence.
- Related ADRs: ADR-0007; ADR-0024
- Related decision logs: `decision-logs/2026-06-03-task-193-chapter6-residual-needs-fix.md`
- Related task id(s): `193`
- Related run id: `799e94f5661f4737ba75b708da636641`
- Related latest.json: `logs/ci/2026-06-03/sc-review-pipeline-task-193/latest.json`
- Related pipeline artifacts: `logs/ci/2026-06-03/sc-review-pipeline-task-193-799e94f5661f4737ba75b708da636641`; `logs/ci/2026-06-03/sc-llm-review-task-193`
- Delivery profile: fast-ship

## Why

Task 193 closes the map tile-id completion requirement by proving that map definitions require at least one tile before completion logic can safely read `tiles[0]`.

## Scope

- Add or update xUnit coverage in `Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs`.
- Add Godot-side or adapter-facing coverage for the player-visible tile-id mapping completion path.
- Preserve deterministic core boundaries and keep `Game.Core` free of `Godot.*` dependencies.
- Record Chapter 3.8 and Chapter 6 evidence under `logs/**`.

## Validation

- `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 193 --tdd-stage red-first --verify unit`
- `py -3 scripts/sc/build.py tdd --task-id 193 --stage green`
- `py -3 scripts/sc/build.py tdd --task-id 193 --stage refactor`
- `py -3 scripts/sc/run_review_pipeline.py --task-id 193 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
- `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`
