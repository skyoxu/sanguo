---


PRD-ID: PRD-SANGUO-V3


Title: V3 Rules Freeze and Assertion Routing


Status: Draft


ADR-Refs:


  - ADR-0003


  - ADR-0004


  - ADR-0005


  - ADR-0010


  - ADR-0015


  - ADR-0019


Arch-Refs:


  - CH01


  - CH02


  - CH03


  - CH06


  - CH07


  - CH10


Test-Refs:


  - scripts/sc/acceptance_check.py


  - scripts/python/validate_acceptance_refs.py


  - scripts/python/validate_acceptance_anchors.py


---





# V3 Rules Freeze and Assertion Routing





This page absorbs the operational meaning of `PRD_V3_RULES_FREEZE.md` and `PRD_V3_ACCEPTANCE_ASSERTIONS.md` into overlay ownership.





## How to Use This Page





- Start here when a task references a V3 freeze or assertion.


- Jump from an assertion to its owner page.


- Use `08-Contracts-Quality-Metrics.md` for gate execution and evidence layout.


- Use `ACCEPTANCE_CHECKLIST.md` for release closure.


- Use owner pages to distinguish currently landed `EventType` constants from additive design targets.





## Global Freeze Boundaries





- Campaign mode in this phase runs with AI disabled.


- Probability tuning belongs to configuration files, not freeze text.


- Non-crash issues do not create user-facing feedback flows.


- Same-frame critical collisions obey one global order:


  1. crash


  2. hard game-over


  3. replay integrity stop


  4. save-path risk state


  5. non-critical UI or logging side effects


- Task-view `contractRefs` may use landed domain events only. Planned contracts stay in overlay text until the C# contract file lands.





## Assertion Routing Matrix





| Assertion | Freeze source | Owner overlay | Primary tasks |


|---|---|---|---|


| A-001 | 2.2 priority chain | `08-t52-turn-window-and-event-ordering.md` | T75, T96, T123, T124 |


| A-002 | 2.1 logical time only | `08-t52-turn-window-and-event-ordering.md` | T96, T123, T124 |


| A-003 | 3.1 mandatory final retry | `08-t52-turn-window-and-event-ordering.md` | T75, T88 |


| A-004 | 3.1 leave allowed after retry fail | `08-t52-turn-window-and-event-ordering.md` | T75, T88 |


| A-005 | 3.2 persistent save warning | `08-t52-turn-window-and-event-ordering.md` | T75, T88 |


| A-006 | 3.3 confirmation default | `08-Contracts-Sanguo-GameLoop-Events.md` | T66, T90, T109 |


| A-007 | 3.4 interaction locking | `08-Contracts-Sanguo-GameLoop-Events.md` | T67, T90, T109 |


| A-008 | 4.1 popup-log atomic commit | `08-Contracts-Sanguo-GameLoop-Events.md` | T68, T81, T92 |


| A-009 | 4.1/4.2 popup overload summary | `08-Contracts-Sanguo-GameLoop-Events.md` | T68, T82, T92 |


| A-010 | 4.3 HUD fixed window + lazy load | `08-Contracts-Sanguo-GameLoop-Events.md` | T68, T82, T92 |


| A-011 | 4.4 release i18n fallback | `08-Contracts-Sanguo-GameLoop-Events.md` | T69, T92, T112 |


| A-012 | 4.4 dev raw-key diagnostics | `08-Contracts-Sanguo-GameLoop-Events.md` | T69, T92, T112 |


| A-013 | 5.1 replay integrity inputs | `08-Contracts-Sanguo-GameLoop-Events.md` | T70, T83, T91, T173 |


| A-014 | 5.2 save_untrusted effect | `08-Contracts-Sanguo-GameLoop-Events.md` | T70, T83, T91, T173 |


| A-015 | 5.3 mismatch policy by mode | `08-Contracts-Sanguo-GameLoop-Events.md` | T70, T84, T91, T173 |


| A-016 | 5.4 diagnostic copy payload | `08-Contracts-Security.md` | T71, T113, T174 |


| A-017 | 5.5 retention window | `08-Contracts-Security.md` | T71, T114, T174 |


| A-018 | 6 audit fallback | `08-Contracts-Security.md` | T72, T115, T174 |


| A-019 | 6 rotation cap | `08-Contracts-Security.md` | T72, T116, T174 |


| A-020 | 7 additive-only contract evolution | `08-contracts-taskmap-t50-t65.md` + `08-Contracts-Quality-Metrics.md` | T73, T151, T175 |






## Governance and Gate Routing Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T80 | PRD v3 assertion gate integration pack | `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.game.ended`; routing owner remains this page while gate execution owner remains `08-Contracts-Quality-Metrics.md` |
| T91 | core assertion gate runner | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.game.ended`; routing owner remains this page while gate execution owner remains `08-Contracts-Quality-Metrics.md` |
| T92 | UI assertion gate runner | `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`; routing owner remains this page while gate execution owner remains `08-Contracts-Quality-Metrics.md` |
| T112 | PRD v3 explainability/replay/i18n hard-gate closure integration pack | none yet; routing-closure task with empty `contractRefs`; semantic owners remain `08-Contracts-Sanguo-GameLoop-Events.md` and `08-Contracts-Quality-Metrics.md` |
| T151 | core assertion hard-gate closure integration pack | none yet; integration-closure task with empty `contractRefs`; semantic owners are `08-Contracts-Sanguo-GameLoop-Events.md`, `08-Contracts-Security.md`, `08-contracts-taskmap-t50-t65.md`, and `08-Contracts-Quality-Metrics.md` |
| T152 | UI assertion hard-gate closure | none yet; UI gate closure task with empty `contractRefs`; semantic owner remains `08-Contracts-Sanguo-GameLoop-Events.md` while execution owner remains `08-Contracts-Quality-Metrics.md` |
| T153 | R4 end-to-end explainability and replayability gate | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`; deterministic scenario gate now binds `contractRefs` to landed replay/explainability runtime events; semantic owners remain `08-feature-slice-t2-monopoly-loop.md` and `08-Contracts-Sanguo-GameLoop-Events.md` |
| T154 | freeze policy guard for non-crash feedback suppression | none yet; security-policy task with empty `contractRefs`; semantic owner remains `08-Contracts-Security.md` |
| T155 | freeze change-control triplet gate | none yet; semantic owner is `08-governance-freeze-change-control.md`; routing stays here while gate execution remains `08-Contracts-Quality-Metrics.md` |
| T156 | signal XML documentation completeness gate | none yet; signal-doc completeness task with empty `contractRefs`; semantic owner remains `08-Contracts-Sanguo-GameLoop-Events.md` |
| T157 / T162 / T163 | signal compliance workflow lane | none yet; semantic owner is `08-governance-signal-compliance-workflow.md`; routing stays here while gate execution remains `08-Contracts-Quality-Metrics.md` |
| T158 | GDScript subscription lifecycle leak guard integration pack | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |
| T159 | privacy-compliance document and policy gate | none yet; privacy-policy task with empty `contractRefs`; semantic owner remains `08-Contracts-Security.md` |
| T160 | logging-guidelines document and lint gate | none yet; semantic owner is `08-governance-logging-policy-and-lint.md`; routing stays here while gate execution remains `08-Contracts-Quality-Metrics.md` |
| T161 / T166 / T167 / T168 | migration compatibility report lane | none yet; semantic owner is `08-governance-migration-compatibility.md`; routing stays here while gate execution remains `08-Contracts-Quality-Metrics.md` |
| T164 | runtime signal subscription lifecycle guard | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |
| T165 | GdUnit signal lifecycle leak fixtures | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |

## Business Acceptance Scenario Ownership





| Task | Concern | Current extant EventType set |


|---|---|---|


| T111 | PRD v3 business acceptance integration suite integration pack | semantic owner: `08-business-acceptance-scenarios.md`; routing stays here; empty `contractRefs` remain intentional |


| T149 | campaign full-loop boss-win scenario | semantic owner: `08-business-acceptance-scenarios.md`; deterministic end-to-end evidence task with empty `contractRefs` |


| T150 | campaign full-loop camp-fail scenario | semantic owner: `08-business-acceptance-scenarios.md`; deterministic end-to-end evidence task with empty `contractRefs` |





- These tasks lock business-flow closure through deterministic evidence rather than through a single runtime event family.


- `T149` proves the campaign can reach final Boss victory without replay or explainability regressions.


- `T150` proves the campaign can terminate on camp durability failure with the correct defeat routing.


- `T111`, `T149`, and `T150` intentionally keep empty `contractRefs`; if future scenario harnesses consume dedicated evidence events, update `08-business-acceptance-scenarios.md`, this page, and both task-view files together.





## Change Control





If any implementation changes freeze sections 2~7, the following must be updated together:





1. `PRD_V3_RULES_FREEZE.md`


2. `PRD_V3_ACCEPTANCE_ASSERTIONS.md`


3. this routing page


4. the concrete owner overlay page


5. the relevant task-view `contractRefs` if the landed event surface changed





If code changes without the routing update, later review loses the ability to judge whether behavior still matches the frozen contract.


