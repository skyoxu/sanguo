---
PRD-ID: PRD-SANGUO-V3
Title: Campaign Security and Privacy Contracts
Status: Draft
ADR-Refs:
  - ADR-0003
  - ADR-0004
  - ADR-0019
Arch-Refs:
  - CH02
  - CH03
  - CH06
  - CH10
Test-Refs:
  - scripts/python/validate_contracts.py
  - scripts/sc/acceptance_check.py
---

# Campaign Security and Privacy Contracts

Owner page for T71~T72, T113~T116, T154, T159, T174, and the security semantic slice of T151.

## Scope

- diagnostic copy payload and desensitization
- retention window
- audit fallback and rotation
- suppression of non-crash user-facing feedback
- evidence path and retention behavior under runtime and CI

## Current Extant Governance Contract Surface

The following generic event constants are already landed and may be used when governance tasks genuinely emit or consume them:

- `core.traceability.checked`
- `core.audit.logged`

## When Empty `contractRefs` Are Acceptable

Governance tasks may keep empty `contractRefs` when they do not own runtime event publication or consumption and only operate on files, policies, or schema gates.

In the current V3 task views:

- T71, T72, T151, T154, T159, and T174 remain valid with empty `contractRefs`
- T113 and T114 intentionally anchor to `core.traceability.checked` and `core.audit.logged`
- T115 and T116 intentionally anchor to `core.audit.logged`

This split is deliberate. It distinguishes pure policy tasks from runtime-auditable governance behavior.

## Frozen Policy

### Diagnostic Payload

- release mode: safety-first
- dev mode: diagnosability-first
- copy action is local-runtime only
- payload is desensitized before any UI-facing or clipboard-facing use
- payload must not include save-path secrets, machine identifiers, or unrestricted raw content-pack dumps

### Retention Window

- keep only the latest 3 runs
- cleanup is triggered at settlement, not at arbitrary log-write time
- cleanup failure writes diagnostics but does not break settlement progression

### Audit Fallback

- runtime continues when the primary audit sink fails
- record an in-memory warning
- attempt fallback write to `user://`
- enforce fixed-size rotation instead of unbounded growth
- fallback write may degrade evidence quality, but it may not silently disappear

### User Feedback Policy

- only crash-class failures may enter explicit user-facing feedback flow
- non-crash issues stay inside logs, audit, and diagnostics summaries
- the policy applies to campaign runtime, replay diagnostics, and content-pack governance screens

## Task Binding

| Task | Policy slice | Domain-event ownership | Required evidence |
|---|---|---|---|
| T71 | diagnostic payload and retention baseline | none by default | desensitization tests, retention summary, cleanup trace |
| T72 | primary-audit failure fallback baseline | none by default | fallback-write tests, rotation-cap summary, warning trace |
| T113 / T114 | diagnostic copy payload and retention enforcement | `core.traceability.checked`, `core.audit.logged` | desensitization tests, retention summary, cleanup trace |
| T115 / T116 | primary-audit failure fallback and rotation cap | `core.audit.logged` | fallback-write tests, rotation-cap summary, warning trace |
| T151 | core assertion hard-gate closure integration pack | none by default; cross-family assertion closure with empty `contractRefs`; security semantic owner remains this page while execution owner remains `08-Contracts-Quality-Metrics.md` | CI summary, schema-valid gate output, artifact path proof |
| T154 | suppress non-crash user feedback | none by default | policy gate summary and UI absence evidence |
| T159 | privacy-compliance document and policy gate | none by default; privacy-policy task with empty `contractRefs` | CI summary, schema-valid gate output, artifact path proof |
| T174 | diagnostic and audit fallback hard-gate integration | none by default; security/audit bundle task with empty `contractRefs` | CI summary, schema-valid gate output, artifact path proof |

## Assertion Ownership

- `A-016`: diagnostic copy payload policy
- `A-017`: diagnostic retention window
- `A-018`: audit fallback on primary write failure
- `A-019`: fallback rotation cap

## Runtime Data Boundaries

Allowed classes of diagnostic data:

- run identifiers
- assertion ids
- sanitized stack or error categories
- content-pack id, version, and fingerprint
- mode and build channel

Disallowed classes of diagnostic data:

- unrestricted clipboard dumps of gameplay state
- raw private filesystem paths beyond policy-approved evidence roots
- user-facing raw security keys or internal token text

## Evidence Requirements

- unit coverage for desensitization, retention, and rotation
- integration coverage for primary sink fail -> fallback write path
- policy gate coverage for non-crash feedback suppression
- schema-valid summaries under `logs/ci/<date>/`

## Stop-the-Line Conditions

- retention policy grows without cap
- fallback write failure is swallowed without a warning artifact
- release path exposes raw diagnostic internals to the player
- governance tasks claim event coverage but the runtime never emits the referenced landed constants
