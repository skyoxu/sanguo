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
- core player fantasy
- minimum playable loop
- scope boundary
- success criteria
- evidence links (video, notes, screenshots, logs, or benchmark summary)
- exit decision: `discard | archive | promote`

## Solo-Dev Absorption
Prototype lane should also support a lightweight solo-developer mindset without becoming a second workflow engine.

Use the following operator questions early:
- what is the core player fantasy?
- what is the minimum playable loop for this prototype?
- what proves this idea should be promoted?
- what proves this idea should be archived?
- what proves this idea should be discarded?

The point is to keep the prototype small, playable, and decision-oriented rather than prematurely complete.

Recommended location:
- `docs/prototypes/` for design-heavy prototypes
- `prototypes/` or feature-local scratch area for code-heavy prototypes


- Full operator flow: `docs/workflows/prototype-lane-playbook.md`

## Prototype TDD Option
If you still want TDD while staying in prototype lane, use the lightweight prototype entrypoint instead of formal Chapter 6 evidence:

- `py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage red --dotnet-target Game.Core.Tests/Game.Core.Tests.csproj --filter <Expr>`
- It writes prototype notes under `docs/prototypes/` and local evidence under `logs/ci/<date>/prototype-tdd-<slug>-<stage>/`.
- It does not consume Taskmaster triplets, acceptance refs, overlay refs, or review sidecars.
- If the prototype is promoted, rerun the work through formal `6.3 -> 6.4 -> 6.5 -> 6.6` instead of treating prototype evidence as production evidence.

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

A good promote decision usually means:
- the core player fantasy is understandable enough to keep
- the minimum playable loop can be executed end to end
- the next formal task is clearer than the remaining prototype uncertainty

A good archive decision usually means:
- the idea is still interesting
- but the loop is not yet strong enough to justify formal delivery
- and keeping the evidence is still useful for later comparison

A good discard decision usually means:
- the loop is not fun enough, clear enough, or viable enough
- and more prototype iteration is unlikely to change that cheaply

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
