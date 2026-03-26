---

PRD-ID: PRD-SANGUO-V3

Title: V3 Quality Metrics and Gate Routing

Status: Draft

ADR-Refs:

  - ADR-0003

  - ADR-0005

  - ADR-0015

Arch-Refs:

  - CH01

  - CH03

  - CH07

  - CH09

  - CH10

Test-Refs:

  - scripts/sc/build.py

  - scripts/sc/acceptance_check.py

  - scripts/python/run_dotnet.py

  - scripts/python/validate_acceptance_refs.py

  - scripts/python/validate_acceptance_anchors.py

---



# V3 Quality Metrics and Gate Routing



Gate-execution owner page for T80, T91~T92, T111~T112, and T151~T175. Semantic governance owner pages for freeze control, signal workflow, logging policy, and migration compatibility remain separate where noted below.



## Hard-Gate Goal



- Turn `A-001~A-020` into executable gates rather than static PRD text.

- Produce machine-readable evidence under `logs/ci/<date>/`.

- Keep core, UI, replay, audit, privacy, and migration evidence under one routing contract.

- Fail with actionable diagnostics instead of generic red lights.



## Entry Points



### TDD Entry



- `py -3 scripts/sc/build.py tdd --task-id <id> --stage green`

- `py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor`



### Acceptance Entry



- `py -3 scripts/sc/acceptance_check.py --task-id <id>`

- subtasks coverage reads main `tasks.json` subtasks plus acceptance coverage semantics from the exported task views



### Contract and Backlink Entry



- `py -3 scripts/python/validate_contracts.py`

- `py -3 scripts/python/check_tasks_all_refs.py`

- `py -3 scripts/python/validate_task_master_triplet.py`

### Extant Contract Anchors

- `Game.Core/Contracts/EventTypes.cs`
- `Game.Core/Contracts/Sanguo/GameEvents.cs`
- `Game.Core/Contracts/Sanguo/SanguoBossChallengePrompted.cs`
- `Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs`
- `Game.Core/Contracts/Sanguo/SanguoLootEvents.cs`
- `Game.Core/Contracts/Sanguo/SanguoObjectiveSkipped.cs`



## Gate Package Ownership



| Gate package | Primary tasks | Assertion range | Event surface expectation |

|---|---|---|---|

| Core assertion gate | T80, T91, T151, T173 | `A-001~A-007`, `A-013~A-015` | lifecycle, replay, forced-challenge, and replay-trust contracts |

| UI assertion gate | T80, T92, T112, T152, T153 | `A-008~A-012` | popup/log/HUD-facing result events |

| Security and audit assertion gate | T71, T72, T113~T116, T151, T174 | `A-016~A-019` | diagnostic payload, retention, audit fallback, and rotation-cap evidence; `T174` itself keeps empty `contractRefs` |

| Compatibility closure gate | T73, T151, T175 | `A-020` | additive-only compatibility sentinel set owned by `08-contracts-taskmap-t50-t65.md` |

| Governance and migration gate | T154~T157, T159~T163, T166~T168 | policy and migration closure | governance and migration tasks intentionally keep empty `contractRefs`; semantic owner pages stay in security and dedicated governance overlays while execution evidence converges here |

| Runtime signal leak guard | T158, T164, T165 | signal subscription lifecycle guard | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |



- The fourth column is bundle-level assertion surface, not a promise that every listed task keeps non-empty `contractRefs`.

- T151, T152, T154, T155, T156, T157, T159, T160, T161, T162, T163, T166, T167, T168, T173, T174, and T175 intentionally keep empty `contractRefs` in the current repository.

- Only T158, T164, and T165 in this governance cluster currently bind landed runtime sentinels.



## Assertion Bundle Routing



### Core Hard-Gate Bundle



- `A-001~A-007`

- `A-013~A-015`

- task anchors: T91, T151, T173

- representative extant events: `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.game.ended`



### Security / Audit Hard-Gate Bundle



- `A-016~A-019`

- task anchors: T151, T174

- representative extant events: `core.traceability.checked`, `core.audit.logged`



### Compatibility Closure Bundle



- `A-020`

- task anchors: T73, T151, T175

- sentinel compatibility set stays owned by `08-contracts-taskmap-t50-t65.md` and is not copied into task-view `contractRefs` for governance splits



### UI / Explainability Hard-Gate Bundle



- `A-008~A-012`

- R4 explainability and replayability non-regression

- task anchors: T92, T112, T152, T153

- representative extant events: `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`



### Governance / Policy Bundle



- T154: non-crash feedback suppression via `08-Contracts-Security.md`

- T155: freeze triplet synchronization gate via `08-governance-freeze-change-control.md`

- T156: signal XML documentation completeness via `08-Contracts-Sanguo-GameLoop-Events.md`

- T157/T162/T163: signal compliance workflow via `08-governance-signal-compliance-workflow.md`

- T158/T164/T165: signal subscription lifecycle leak guard via `08-feature-slice-t2-monopoly-loop.md`

- T159: privacy policy gate via `08-Contracts-Security.md`

- T160: logging guideline and lint policy via `08-governance-logging-policy-and-lint.md`

- T161/T166~T168: migration compatibility report automation via `08-governance-migration-compatibility.md`



## Task Ownership Detail



| Task | Concern | Current extant EventType set |

|---|---|---|

| T151 | core assertion hard-gate closure integration pack | none yet; integration-closure task with empty `contractRefs`; semantic owners remain `08-Contracts-Sanguo-GameLoop-Events.md`, `08-Contracts-Security.md`, and `08-contracts-taskmap-t50-t65.md` |

| T152 | UI assertion hard-gate closure | none yet; UI gate closure task with empty `contractRefs`; semantic owner remains `08-Contracts-Sanguo-GameLoop-Events.md` |

| T153 | R4 end-to-end explainability and replayability gate | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`; end-to-end gate now binds `contractRefs` to landed replay-trust and explainability runtime events; semantic owners remain `08-feature-slice-t2-monopoly-loop.md` and `08-Contracts-Sanguo-GameLoop-Events.md` |

| T173 | replay integrity and mismatch policy hard-gate bundle | none yet; assertion bundle task with empty `contractRefs`; semantic owner remains `08-Contracts-Sanguo-GameLoop-Events.md` |

| T174 | diagnostic and audit fallback hard-gate bundle | none yet; security/audit assertion bundle with empty `contractRefs`; semantic owner remains `08-Contracts-Security.md` |

| T175 | additive-only compatibility closure hard-gate | none yet; compatibility closure task with empty `contractRefs`; semantic owner remains `08-contracts-taskmap-t50-t65.md` |



## Governance Owner Handoff



- `T155` -> `08-governance-freeze-change-control.md`

- `T157`, `T162`, `T163` -> `08-governance-signal-compliance-workflow.md`

- `T160` -> `08-governance-logging-policy-and-lint.md`

- `T161`, `T166`, `T167`, `T168` -> `08-governance-migration-compatibility.md`



## Summary Schema and Post-Evidence Gate



- Gate summaries must pass JSON-schema validation before any aggregated review or unified pipeline step consumes them.

- `sc-test` and `acceptance_check` summaries are schema-checked first; schema failure is a hard stop, not a warning.

- Post-evidence integration gate runs only after `headless-e2e-evidence` succeeds.

- If headless evidence fails, the post-evidence gate must report `skipped(reason=headless_e2e_evidence_failed)` rather than executing a misleading second failure.



## Evidence Layout



- `A-001~A-005` -> `logs/ci/<date>/assertions/prd-v3-core.json`

- `A-006~A-012` -> `logs/ci/<date>/assertions/prd-v3-ui.json`

- `A-013~A-015` -> `logs/ci/<date>/assertions/prd-v3-replay.json`

- `A-016~A-019` -> `logs/ci/<date>/assertions/prd-v3-audit.json`

- `A-020` -> contract compatibility summary



## Output Contract



Every summary must include at least:



- `assertion_id`

- `task_id`

- `gate_name`

- `status`

- `reason`

- `evidence_path`



A hard-gate failure is invalid if it only reports a generic `fail` without enough context to identify the assertion, task, and evidence location.



## Stop-the-Line Rules



- A gate fails schema validation.

- A post-evidence gate runs after headless evidence already failed.

- A quality summary points to an event family that does not exist in `Game.Core/Contracts`.

- A task view claims assertion coverage but omits the extant event surface it is gating.

