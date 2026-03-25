# Prototype Lane

Purpose: separate **exploration work** from **formal delivery work**.

Prototype lane is **not** another `DELIVERY_PROFILE`. Delivery profiles control how strict a formal task run should be. Prototype lane controls whether the work should enter the formal task/review/acceptance pipeline at all.

## What Prototype Lane Is For
Use prototype lane when the question is still:
- Is this mechanic worth building?
- Is this loop fun enough to keep?
- Is this UI interaction understandable?
- Is this architecture option viable enough to promote?
- Is this prompt/review strategy worth turning into a formal workflow?

## What Prototype Lane Is Not For
Do not use prototype lane when the work already:
- ships to players,
- modifies long-lived save compatibility,
- becomes part of the formal release branch,
- needs full task completion in `.taskmaster/tasks/*.json`,
- or must satisfy production-quality acceptance and review gates.

## Difference From EA / Delivery Profiles
- `prototype lane`
  - answers: **should this become real work?**
  - outcome: `discard`, `archive`, or `promote`
- `playable-ea / fast-ship / standard`
  - answer: **how strict should formal delivery be once the work is real?**
  - outcome: a shippable or near-shippable task result under the chosen profile

## Minimum Required Artifacts
Every prototype should record:
- hypothesis
- scope boundary
- success criteria
- evidence links (video, notes, screenshots, logs, or benchmark summary)
- exit decision: `discard | archive | promote`

Recommended location:
- `docs/prototypes/` for design-heavy prototypes
- `prototypes/` or feature-local scratch area for code-heavy prototypes

## Allowed Relaxations
Prototype lane may relax:
- full `run_review_pipeline.py` usage
- full semantic review strictness
- full acceptance authoring
- full task triplet integration
- release-grade coverage targets

## Hard Boundaries That Still Stay
Prototype lane does **not** allow:
- unsafe path / host / network behavior beyond the active security baseline
- silent drift in `Game.Core/Contracts/**`
- pretending a prototype is a completed formal task
- mixing throwaway experiment code into long-lived formal modules without a promotion step
- hiding prototype debt in production files without an explicit follow-up plan

## Promotion Rule
Promote a prototype into formal delivery only after it has a clear keep decision.

Promotion should add or update:
- real task entries in `.taskmaster/tasks/*.json`
- overlay refs / test refs / acceptance refs
- formal contracts if the prototype changes domain boundaries
- deterministic tests and the correct delivery-profile review path

## Recommended Operator Flow
1. Create the prototype with a written hypothesis.
2. Run only the minimum checks needed to keep the repo safe.
3. Decide `discard`, `archive`, or `promote` quickly.
4. If promoted, rewrite or relocate the result into the formal task pipeline instead of treating the prototype artifact as done.
