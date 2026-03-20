---
PRD-ID: PRD-SANGUO-V3
Title: V3 Reward Draft and Commit Path (Compatibility Filename)
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
Test-Refs:
  - Game.Core.Tests/Tasks/Task57ActionCardPolicyTests.cs
  - Game.Core.Tests/Tasks/Task57ActionCardWindowTests.cs
---

# V3 Reward Draft and Commit Path

Compatibility note: this page keeps the historical filename `08-t57-action-cards.md` because the task triplet still points here, but the V3 ownership in this page is reward-draft specific.

Owner page for T78, T119, and T120.

## RewardDraftEngine Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T78 | deterministic 3-choice reward draft integration | `core.sanguo.loot.granted`, `core.sanguo.relic.applied`, `core.sanguo.action_card.played`, `core.sanguo.action_card.play.rejected` |
| T119 / T120 | candidate stability, commit path, and source-tag closure | `core.reward.offer.presented`, `core.reward.offer.selected`, `core.reward.offer.skipped` |

## Goal

- Present deterministic reward candidates after objective or Boss reward generation.
- Keep candidate ordering stable under the same seed and content inputs.
- Preserve explainability and replay evidence across present, select, skip, and commit paths.

## Runtime Rules

- Candidate generation is deterministic under the same seed and content-pack identity.
- Commit must record both the selected reward and the originating reward-source tag.
- Skip is an explicit branch, not an implicit disappearance of the draft.
- Final reward commit must stay aligned with later explainability and replay summaries.

## Current vs Planned Contract Surface

Extant task-view event set:

- `core.sanguo.loot.granted`
- `core.sanguo.relic.applied`
- `core.sanguo.action_card.played`
- `core.sanguo.action_card.play.rejected`
- `core.reward.offer.presented`
- `core.reward.offer.selected`
- `core.reward.offer.skipped`

Notes on extant surface:

- The `core.reward.offer.*` family is currently landed as generic compatibility constants in `Game.Core/Contracts/EventTypes.cs`.
- The `core.sanguo.*` reward events remain the concrete Sanguo-side result signals after the draft is committed.

Planned additive names that stay in overlay text for now:

- `core.sanguo.reward.draft.opened`
- `core.sanguo.reward.draft.committed`

## Explainability Requirement

- UI summary must show source, candidate choice, and final committed reward.
- Replay evidence must preserve the candidate set, not only the chosen result.
- Draft presentation, selection, skip, and commit must all stay attributable to one correlation chain.

## Key Outputs

- reward candidate set
- presentation order record
- select or skip decision
- committed reward with source tag
- replay-trust evidence for the draft branch
