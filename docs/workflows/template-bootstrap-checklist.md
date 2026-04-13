# Template Bootstrap Checklist

## Purpose

Use this checklist right after copying this template into a new game repository.

It is intentionally narrow:

- first-pass identity replacement
- first-pass workflow and profile alignment
- first-pass task and docs wiring
- first-pass local validation

This is not a full migration guide. It is the minimum path to get a copied project into a non-misleading state.

## Stop-Loss Rule

Do not start feature work before these items are done.

If project identity, workflow names, profile defaults, and task sources still point to the template, later ADR work, overlays, and agent runs will drift immediately.

## Step 1: Replace Project Identity

Update the first-layer identity files:

- `project.godot`
- `README.md`
- repository badges and workflow links in `README.md`
- user-facing quick-start docs such as `docs/TEMPLATE_GODOT_GETTING_STARTED.md`

Check for stale template naming in docs:

- old repository name
- old product name
- old PRD id examples
- old workflow names in badges or links

## Step 2: Choose The Default Delivery Profile

Decide the default project posture in:

- `scripts/sc/config/delivery_profiles.json`

Recommended starting points:

- `playable-ea`: playable proof, fastest iteration, lightest gates
- `fast-ship`: default for most new single-player business repos
- `standard`: milestone or release-hardening posture

Then verify these still match project intent:

- `DELIVERY_PROFILE.md`
- `README.md`
- `.github/workflows/ci-windows.yml`
- `.github/workflows/windows-quality-gate.yml`

Do not change the profile catalog in one place and leave workflow defaults or docs behind.

## Step 3: Review Security Mapping

Confirm that the derived security posture is still intentional:

- `playable-ea` -> `host-safe`
- `fast-ship` -> `host-safe`
- `standard` -> `strict`

For Windows-only single-player repos, this mapping is usually enough.

Do not add anti-tamper-heavy policy by default unless the business repo explicitly needs it.

## Step 4: Replace Template Task Sources When Real Tasks Exist

If the new project has real task data, replace template fallback assumptions with the actual files under:

- `.taskmaster/tasks/tasks.json`
- `.taskmaster/tasks/tasks_back.json`
- `.taskmaster/tasks/tasks_gameplay.json`

Then re-check any scripts or workflows that reference task files directly.

If the project is still in pure template mode, keep the fallback behavior explicit instead of pretending real task data exists.

## Step 5: Seed PRD / Overlay / ADR Routing

Before feature work, set the first real routing anchors:

- create the real PRD identifier under `docs/architecture/overlays/<PRD-ID>/`
- confirm accepted ADR coverage in `docs/architecture/ADR_INDEX_GODOT.md`
- keep contract SSoT under `Game.Core/Contracts/**`

Do not move contracts into docs or scene folders.

If a copied project changes posture, add or supersede ADRs early instead of carrying template assumptions silently.

## Step 6: Review Workflow Names, Secrets, And Release Behavior

Check these surfaces after copying:

- workflow file names under `.github/workflows/`
- README badge targets
- release workflow triggers
- Sentry secrets and Step Summary expectations
- project-specific export and smoke assumptions

The common failure mode is simple: the copied repo runs, but its badges, release names, or summary language still point at the template or a sibling repo.

## Step 7: Review Agent And Recovery Entry Points

Confirm the new repo still points to the correct recovery documents:

- `AGENTS.md`
- `docs/agents/00-index.md`
- `docs/workflows/run-protocol.md`
- `execution-plans/`
- `decision-logs/`

If you change repository defaults, also update:

- `DELIVERY_PROFILE.md`
- `docs/agents/10-template-customization.md`
- `scripts/sc/README.md`

## Step 8: Run A First Local Baseline Check

Run a small baseline pass before starting features:

```powershell
py -3 scripts/python/validate_recovery_docs.py
py -3 scripts/python/validate_contracts.py
py -3 scripts/sc/run_review_pipeline.py --task-id <task-id> --dry-run --skip-llm-review --skip-agent-review
```

Notes:

- if the copied repo already has real Taskmaster data, use a real task id instead of `1`
- if the repo changed contract or task layout, fix that before trusting the dry run
- if the repo is still in template mode, keep the dry run as a structure check only

## Step 8.5: Optional OpenAI Backend Bootstrap

Only do this when the business repo deliberately wants to pilot model-backed workflow families away from `codex-cli`:

```powershell
py -3 -m pip install openai
$env:OPENAI_API_KEY = "<your-key>"
py -3 scripts/sc/llm_review.py --self-check --llm-backend openai-api
py -3 scripts/sc/llm_extract_task_obligations.py --self-check --llm-backend openai-api
py -3 scripts/sc/llm_align_acceptance_semantics.py --self-check --llm-backend openai-api
py -3 scripts/sc/llm_fill_acceptance_refs.py --self-check --llm-backend openai-api
py -3 scripts/sc/llm_check_subtasks_coverage.py --self-check --llm-backend openai-api
py -3 scripts/sc/llm_semantic_gate_all.py --self-check --llm-backend openai-api
```

Optional TDD-family spot check after the semantic family is clean:

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --help
```

Notes:

- current template behavior still defaults to `codex-cli`
- `openai-api` is still an explicit opt-in backend rather than the default
- the safest bootstrap order is: `llm_review` first, semantic family second, test generation last
- treat `--self-check` as the first stop-loss; do not wire the backend into CI before self-check is clean
- `llm_generate_tests_from_acceptance_refs.py` has no deterministic self-check mode yet, so use `--help` first and only pilot it after the semantic family is already stable on the chosen backend

## Step 9: Define First Success Criteria

A copied repo is minimally aligned only when:

- identity files no longer point to the template
- default delivery profile is deliberate, not accidental
- workflow names and secrets match the new repo
- task sources are either real or explicitly still template fallback
- contracts stay under `Game.Core/Contracts/**`
- local recovery docs validate
- one dry-run pipeline can complete without misleading paths or names

## Related Docs

- `README.md`
- `DELIVERY_PROFILE.md`
- `docs/agents/10-template-customization.md`
- `docs/workflows/run-protocol.md`
- `docs/workflows/overlays-authoring-guide.md`
- `docs/workflows/contracts-template-v1.md`

