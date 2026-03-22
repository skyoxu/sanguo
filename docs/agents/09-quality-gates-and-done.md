# Quality Gates And DoD

Use this document when you need the old AGENTS content for security baseline, test organization, logs and artifacts, quality gates, or Definition of Done.

## Primary Sources
- [../testing-framework.md](../testing-framework.md): tests, Test-Refs, logs, evidence expectations, and naming rules.
- `scripts/sc/README.md`: local pipeline entry points, profile-aware orchestration, and script-level behavior.
- [../../DELIVERY_PROFILE.md](../../DELIVERY_PROFILE.md): strictness model for `playable-ea`, `fast-ship`, and `standard`.
- `docs/architecture/base/02-security-baseline-godot-v2.md`
- `docs/architecture/base/03-observability-sentry-logging-v2.md`
- `docs/architecture/base/07-dev-build-and-gates-v2.md`
- `docs/architecture/base/09-performance-and-capacity-v2.md`
- [../architecture/ADR_INDEX_GODOT.md](../architecture/ADR_INDEX_GODOT.md)

## Read By Task
- Need to add or repair unit, GdUnit4, or acceptance tests:
  - Read `docs/testing-framework.md`.
- Need to run the unified local pipeline or debug a failed gate:
  - Read `scripts/sc/README.md`, [04-closed-loop-testing.md](04-closed-loop-testing.md), and [03-persistent-harness.md](03-persistent-harness.md).
- Need release hardening or stronger CI posture:
  - Read `DELIVERY_PROFILE.md`, base chapters 02/03/07/09, and the ADR index.
- Need logs, evidence, or artifact locations:
  - Read `docs/testing-framework.md` and [01-session-recovery.md](01-session-recovery.md).

## Definition Of Done Routing
- Architecture or guardrail changes:
  - Check accepted ADRs first and update/add ADRs when the decision changes.
- Code and test changes:
  - Produce the evidence required by the active delivery profile.
- Contracts, overlays, or references changed:
  - Update links, Test-Refs, and task or overlay references where required.
- Local and CI gates:
  - Use `scripts/sc/README.md` and the workflow files in `.github/workflows/`.

## Old AGENTS Coverage Map
- `5 Security & Privacy Baseline` -> base chapter 02 + ADR-0019 + ADR-0031
- `6.2/6.3/6.5 tests, logs, Test-Refs` -> `docs/testing-framework.md`
- `7 Quality Gates (CI/CD)` -> `scripts/sc/README.md` + base chapters 07/09 + `.github/workflows/`
- `8 Definition of Done (DoD)` -> this document + `docs/testing-framework.md`
