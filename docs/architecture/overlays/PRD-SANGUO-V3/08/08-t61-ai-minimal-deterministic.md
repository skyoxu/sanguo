---
PRD-ID: PRD-SANGUO-V3
Title: V3 Campaign AI Disable Guard
Status: Draft
ADR-Refs:
  - ADR-0005
Arch-Refs:
  - CH06
  - CH07
Test-Refs:
  - Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs
---

# V3 Campaign AI Disable Guard

Owner page for T79 and T108.

## AiGuard Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T79 | campaign-mode hard-disable guard | `core.sanguo.ai.decision.made` |
| T108 | runtime regression guard | `core.run.continue.blocked`, `core.sanguo.ai.decision.made` |

## Rule

- Campaign mode in this version runs with AI disabled.
- This is a runtime guard, not physical deletion of the AI module.

## Reason

- Existing AI is deeply connected to the current loop and test assets.
- Removing it physically would create avoidable regression surface.

## Guard Shape

- campaign start payload must carry explicit AI-disabled semantics
- any campaign path reaching AI decision emission is a hard regression
- attempts to continue through an AI-owned runtime branch should be blocked explicitly, with `core.run.continue.blocked` as the current extant compatibility marker
- non-campaign modes may continue using the existing AI path

## Acceptance Focus

- campaign start payload exposes AI-disabled semantics explicitly
- there is no runtime path that enables AI inside campaign rounds
- `core.sanguo.ai.decision.made` in campaign evidence must be absent, not ignored
- any blocked continue path must remain deterministic and auditable
