---

PRD-ID: PRD-SANGUO-V3

Title: 08 Feature Slice Index (V3 Campaign Mode)

Status: Accepted

ADR-Refs:

  - ADR-0003

  - ADR-0004

  - ADR-0005

  - ADR-0010

  - ADR-0015

Arch-Refs:

  - CH01

  - CH03

  - CH06

  - CH07

  - CH10

Test-Refs:

  - scripts/python/validate_task_overlays.py

  - scripts/python/validate_task_master_triplet.py

  - scripts/python/validate_contracts.py

---



# PRD-SANGUO-V3 Feature Slice Index



This directory is the V3 campaign overlay root. It is driven by:



- `prd_v3.md`

- `PRD_V3_TRACEABILITY_MATRIX.md`

- `PRD_V3_RULES_FREEZE.md`

- `PRD_V3_ACCEPTANCE_ASSERTIONS.md`

- `.taskmaster/tasks/tasks.json`

- `.taskmaster/tasks/tasks_back.json`

- `.taskmaster/tasks/tasks_gameplay.json`



Compatibility note:

Some filenames intentionally keep old T2-oriented names so the task triplet can migrate with minimal churn. File content is V3-specific even when the filename is compatibility-oriented.



## Directory Role



- Provide stable overlay targets for `T66~T175`.

- Concentrate V3 rules freeze, acceptance assertions, task decomposition, contracts, gates, and evidence routing in one place.

- Keep base chapters clean; only V3 slice-specific mapping lives here.

- Separate current extant contract surface from planned additive surface so task views can keep `contractRefs` honest.



## Document Groups



### Rules Freeze and Assertion Routing



- `08-rules-freeze-and-assertion-routing.md`

- `08-business-acceptance-scenarios.md`

  - Routes `PRD_V3_RULES_FREEZE.md` and `PRD_V3_ACCEPTANCE_ASSERTIONS.md` into concrete owner pages.

  - Covers `A-001~A-020`.

  - Routes `T111`, `T149`, and `T150`; semantic owner page is `08-business-acceptance-scenarios.md`.

  - Defines the rule that task-view `contractRefs` may only use landed `EventType` constants.



### Governance Owner Pages



- `08-governance-freeze-change-control.md`

  - Semantic owner page for `T155`.

  - Keeps freeze revision, assertion update, and executable evidence update in one change-control triplet.

- `08-governance-signal-compliance-workflow.md`

  - Semantic owner page for `T157`, `T162`, and `T163`.

  - Owns signal-compliance aggregation and workflow hard-gate wiring semantics.

- `08-governance-logging-policy-and-lint.md`

  - Semantic owner page for `T160`.

  - Owns structured logging, redaction, and lint-policy semantics.

- `08-governance-migration-compatibility.md`

  - Semantic owner page for `T161`, `T166`, `T167`, and `T168`.

  - Owns migration-report generation, completeness validation, and CI hard-gate semantics.



### Contracts and Gates



- `08-Contracts-Sanguo-GameLoop-Events.md`

  - Campaign events, DTO expectations, explainability, replay-trust fields.

  - Separates extant runtime events from planned additive contracts.

  - Covers both Sanguo-specific records and extant generic compatibility constants from `Game.Core/Contracts/EventTypes.cs`.

  - Owns `T145`, `T146`, `T156`, `T169`, and `T170`, plus the semantic contract side of `T151`, `T152`, `T153`, and `T173`.

  - Assertion owner: `A-006~A-015`.

- `08-Contracts-Security.md`

  - Diagnostic payload, retention, audit fallback, non-crash feedback suppression.

  - Distinguishes empty-governance tasks from tasks that intentionally use `core.traceability.checked` or `core.audit.logged`.

  - Owns `T154`, `T159`, and the semantic security side of `T174`.

  - Assertion owner: `A-016~A-019`.

- `08-Contracts-Quality-Metrics.md`

  - Gate entry points, schema validation, post-evidence integration hard gate, CI bundles.

  - Owns hard-gate execution for `T80`, `T91~T92`, `T111~T112`, and `T151~T175`; semantic governance owner pages remain separate where noted.

  - Assertion gate routing: `A-001~A-020`.

- `08-contracts-taskmap-t50-t65.md`

  - Contract evolution, sentinel compatibility set, content schema, compatibility mapping.

  - Owns `T147`, `T148`, `T171`, `T172`, and the semantic compatibility side of `T151` and `T175`.

  - Assertion owner: `A-020`.



### Runtime and Feature Slices



- `08-feature-slice-t2-monopoly-loop.md`

  - RunMode split, main runtime loop, signal lifecycle, replay or explainability handoff.

  - Owns `T158`, `T164`, `T165`, and the runtime-loop side of `T153`.

- `08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md`

  - System composition page for setup, commander, board semantics, rewards, buildings, and end conditions.



### Task Pages



- `08-t50-game-start-config.md`: T93

- `08-t52-turn-window-and-event-ordering.md`: T75, T87-T88, T96, T123-T124, owner of `A-001~A-005`

- `08-t54-new-game-menu.md`: T95

- `08-t55-characters.md`: T94, T121-T122

- `08-t56-random-events.md`: T77, T105, T117-T118, T139-T140

- `08-t57-action-cards.md`: T78, T119-T120

- `08-t58-buildings.md`: T97-T99, T125-T128

- `08-t60-game-end-and-settlement.md`: T74, T85-T86, T100, T107, T129-T130, T143-T144

- `08-t61-ai-minimal-deterministic.md`: T79, T108

- `08-t62-relics.md`: T106, T141-T142

- `08-t63-global-events.md`: T76, T89-T90, T101-T103, T131-T136



## Indexed Task Families (T66~T120)



| Task family | Primary owner page | Why the backlink exists |

|---|---|---|

| T66~T70 | `08-Contracts-Sanguo-GameLoop-Events.md` | forced-challenge prompt, explainability popup-log policy, i18n exposure, and replay-trust baseline |

| T71~T72 | `08-Contracts-Security.md` | diagnostic payload, retention, audit fallback, and rotation-cap policy |

| T73 | `08-contracts-taskmap-t50-t65.md` | additive-only compatibility sentinel closure |

| T74 | `08-t60-game-end-and-settlement.md` | campaign rule-engine endgame routing entry pack |

| T75 | `08-t52-turn-window-and-event-ordering.md` | camp lifecycle sequencing and leave-camp retry behavior |

| T76 | `08-t63-global-events.md` | Boss-pressure engine integration baseline |

| T77 | `08-t56-random-events.md` | objective pacing-compensation loop |

| T78 | `08-t57-action-cards.md` | deterministic three-choice reward draft entry pack |

| T79 | `08-t61-ai-minimal-deterministic.md` | campaign-mode AI hard-disable guard |

| T80 | `08-rules-freeze-and-assertion-routing.md` + `08-Contracts-Quality-Metrics.md` | PRD V3 assertion-gate integration root |

| T81~T84 | `08-Contracts-Sanguo-GameLoop-Events.md` | popup-log atomic commit, HUD windowing, replay-trust hash, and mismatch policy splits |

| T85~T86 | `08-t60-game-end-and-settlement.md` | run-mode isolation and endgame adjudicator splits |

| T87~T88 | `08-t52-turn-window-and-event-ordering.md` | one-action camp rule and leave-camp save warning splits |

| T89~T90 | `08-t63-global-events.md` | Boss pressure timeline and forced-challenge preemption splits |

| T91~T92 | `08-rules-freeze-and-assertion-routing.md` + `08-Contracts-Quality-Metrics.md` | split core/UI assertion gate runners |

| T93~T110 | task-specific owner pages listed below | start payload, commander pick flow, HUD config, runtime state machine, camp buildings, Boss pressure, board restrictions, reward routing, contract DTO mapping, and content-pack schema |

| T111~T112 | `08-business-acceptance-scenarios.md` + `08-rules-freeze-and-assertion-routing.md` + `08-Contracts-Quality-Metrics.md` | business-acceptance scenario ownership plus explainability/replay/i18n gate closure |



## Indexed Task Families (T121~T150)



| Task family | Primary owner page | Why the backlink exists |

|---|---|---|

| T121~T122 | `08-t55-characters.md` | commander roster lock/open and active/passive strategem selection guard |

| T123~T124 | `08-t52-turn-window-and-event-ordering.md` | camp-pressure-board sequencing and replay-stability ordering |

| T125~T128 | `08-t58-buildings.md` | five-slot camp durability, persistence, and building-effect routing |

| T129~T130 | `08-t60-game-end-and-settlement.md` | camp durability fatal preemption and camp-fail settlement routing |

| T131~T136 | `08-t63-global-events.md` | Boss profile, pressure, reveal-delay, and forced-challenge hard-cap rules |

| T137~T138 | `08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md` | event-tile auto-trigger and blocked-skip matrix in the assembled board flow |

| T139~T140 | `08-t56-random-events.md` | objective publish timing and terminal suppression |

| T141~T142 | `08-t62-relics.md` | reward-source integration and deterministic reward draft hook |

| T143~T144 | `08-t60-game-end-and-settlement.md` | victory/defeat adjudication branches |

| T145~T146 | `08-Contracts-Sanguo-GameLoop-Events.md` | contract-set completion and HUD DTO mapper closure |

| T147~T148 | `08-contracts-taskmap-t50-t65.md` | content schema extension and content quality-gate closure |

| T149~T150 | `08-business-acceptance-scenarios.md` + `08-rules-freeze-and-assertion-routing.md` | deterministic acceptance-scenario ownership and routing tasks |



## Indexed Task Families (T151~T175)



| Task family | Primary owner page | Why the backlink exists |

|---|---|---|

| T151~T153 | semantic owner pages plus `08-Contracts-Quality-Metrics.md` | core/UI hard-gate closure and R4 replay-explainability evidence stay executable instead of collapsing into a routing-only page |

| T154 | `08-Contracts-Security.md` | non-crash feedback suppression remains a security policy boundary |

| T155 | `08-governance-freeze-change-control.md` | freeze revision, assertion update, and executable evidence update stay locked as one change-control triplet |

| T156 | `08-Contracts-Sanguo-GameLoop-Events.md` | signal XML documentation completeness remains contract-governance work rather than workflow wiring |

| T157/T162/T163 | `08-governance-signal-compliance-workflow.md` + `08-Contracts-Quality-Metrics.md` | signal compliance aggregation and CI hard-gate wiring keep a dedicated workflow owner page |

| T158/T164/T165 | `08-feature-slice-t2-monopoly-loop.md` | runtime subscription lifecycle leak guards stay attached to the runtime-loop owner |

| T159 | `08-Contracts-Security.md` | privacy compliance remains a security-owner policy gate |

| T160 | `08-governance-logging-policy-and-lint.md` | logging policy, redaction, and lint expectations stay under a dedicated observability-governance owner |

| T161/T166/T167/T168 | `08-governance-migration-compatibility.md` + `08-Contracts-Quality-Metrics.md` | migration report generation, completeness validation, and CI hard gate stay one governance family |

| T169~T170 | `08-Contracts-Sanguo-GameLoop-Events.md` | additive contract set and runtime-field harmonization stay in contract governance |

| T171~T172 | `08-contracts-taskmap-t50-t65.md` | compatibility constants and content-task mapping remain additive-only governance work |

| T173 | `08-Contracts-Sanguo-GameLoop-Events.md` + `08-Contracts-Quality-Metrics.md` | replay mismatch policy closure remains a stop-the-line assertion bundle |

| T174 | `08-Contracts-Security.md` + `08-Contracts-Quality-Metrics.md` | diagnostic and audit fallback closure remains a security-owned hard gate |

| T175 | `08-contracts-taskmap-t50-t65.md` + `08-Contracts-Quality-Metrics.md` | additive-only compatibility closure remains a dedicated release gate |



### Acceptance Root



- `ACCEPTANCE_CHECKLIST.md`

  - Release-facing checklist page for V3 implementation closure.



## Assertion Owner Routing



- `A-001~A-005` -> `08-t52-turn-window-and-event-ordering.md`

- `A-006~A-015` -> `08-Contracts-Sanguo-GameLoop-Events.md`

- `A-016~A-019` -> `08-Contracts-Security.md`

- `A-020` -> `08-contracts-taskmap-t50-t65.md` + `08-Contracts-Quality-Metrics.md`



## contractRefs Hygiene



- `contractRefs` in task views list only landed `EventType` constants.

- Those constants may come from either `Game.Core/Contracts/Sanguo` or `Game.Core/Contracts/EventTypes.cs`, but they must already exist in C#.

- Planned V3 names such as `core.sanguo.camp.entered` or `core.sanguo.objective.published` belong in overlay text only until contract files land.

- Governance tasks may keep empty `contractRefs` when they do not own runtime event publication or consumption.

<!-- TASK_BASELINE_START -->
```json
{
  "generated_at": "2026-04-06T08:35:23.786611+00:00",
  "files": [
    {
      "path": ".taskmaster/tasks/tasks.json",
      "exists": true,
      "sha256": "7bddf1a8166ec6d595fc70516668625016453eae238545082baff34134e58186",
      "bytes": 243336
    },
    {
      "path": ".taskmaster/tasks/tasks_back.json",
      "exists": true,
      "sha256": "fba74d589014fdf340425ffc73eac770239d184a06cfdc362243fcc08ae41c23",
      "bytes": 488662
    },
    {
      "path": ".taskmaster/tasks/tasks_gameplay.json",
      "exists": true,
      "sha256": "00884f9f55ebb9f756b6fa2089fedc6cfa999042bf1e919b9056e8b3d90259a0",
      "bytes": 394226
    }
  ]
}
```
<!-- TASK_BASELINE_END -->
