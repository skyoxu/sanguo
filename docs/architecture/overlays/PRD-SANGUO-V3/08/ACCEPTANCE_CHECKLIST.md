---

PRD-ID: PRD-SANGUO-V3

Title: V3 Campaign Acceptance Checklist

Status: Draft

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

  - scripts/sc/acceptance_check.py

  - scripts/python/validate_acceptance_refs.py

  - scripts/python/validate_acceptance_anchors.py

  - scripts/python/validate_task_test_refs.py

---



# V3 Campaign Acceptance Checklist



This page closes the loop between `prd_v3.md`, `PRD_V3_RULES_FREEZE.md`, `PRD_V3_ACCEPTANCE_ASSERTIONS.md`, and execution tasks `T66~T175`.



> Compatibility note: some filenames remain T2-shaped so the task triplet can migrate safely. The checklist itself is V3-specific.



## 一、文档完整性验收



- [ ] `docs/architecture/overlays/PRD-SANGUO-V3/08/_index.md` exists and indexes the V3 pages.

- [ ] `docs/architecture/overlays/PRD-SANGUO-V3/08/08-rules-freeze-and-assertion-routing.md` exists and routes `A-001~A-020`.

- [ ] dedicated governance owner pages exist for freeze change control, signal compliance workflow, logging policy, and migration compatibility.

- [ ] `tasks.json` routes `T66~T175` into V3 overlay pages.

- [ ] `tasks_back.json` and `tasks_gameplay.json` include the required V3 overlay anchors.



## 二、架构设计验收



- [ ] Campaign mode uses explicit `RunMode` isolation instead of mixing old eliminate/bankrupt rules.

- [ ] Runtime ordering is fixed as camp -> pressure or boss branch -> objective publish -> board phase.

- [ ] Replay ordering uses logical `Tick/Round` rather than wall-clock.

- [ ] Global same-frame priority follows `A-001`.

- [ ] Leave-camp save retry, persistent warning, and force-challenge confirmation follow `A-003~A-007`.

- [ ] Non-crash issues never open a user-facing feedback flow.



## 三、代码实现验收



- [ ] Start payload contains `RunMode`, commander, strategem, map, seed, and content-pack identity.

- [ ] Camp uses five building slots and building durability zero is permanent for the current run.

- [ ] Camp allows exactly one camp action per round.

- [ ] Boss pressure includes round, difficulty, reveal delay stacking, and force-challenge cap.

- [ ] Objectives publish and settle in the frozen order, and do not publish after terminal endgame.

- [ ] Event tiles are auto-triggered; skip is not a normal escape path.

- [ ] New events and DTOs obey ADR-0004 naming and additive-only evolution.

- [ ] Contracts stay under `Game.Core/Contracts`; UI does not branch on raw JSON.

- [ ] Content schema covers commander, strategem, camp building, boss, and objective.

- [ ] `pack/version/content_fingerprint` enters save header and replay integrity inputs.



## 四、测试框架验收



- [ ] `A-001~A-005` are covered by core assertion hard gates.

- [ ] `A-006~A-012` are covered by UI or explainability hard gates.

- [ ] `A-013~A-015` are covered by replay hard gates.

- [ ] `A-016~A-019` are covered by audit/privacy hard gates.

- [ ] `A-020` is covered by contract compatibility hard gate.

- [ ] Popup emission and HUD or log write happen in one logical commit.

- [ ] Release build never exposes raw i18n keys to the player UI; dev mode may expose them diagnostically.

- [ ] Replay integrity includes seed, runtime version, content-pack hash, and key-event sequence hash.

- [ ] `save_untrusted` disables deterministic replay certification for the current run context.

- [ ] Diagnostic copy payload is desensitized and retention keeps only the latest 3 runs.

- [ ] Audit primary-write failure falls back to `user://` rotation without interrupting runtime.

- [ ] `sc-build tdd --stage green` still enforces 90/85 coverage baseline.

- [ ] `sc-build tdd --stage refactor` still validates acceptance refs, anchors, test refs, and contracts.

- [ ] CI output can locate the exact gate, assertion, task, and evidence path.



## Task-Family Closure Anchors (T66~T120)



| Task family | Checklist closure anchor | Closure meaning |

|---|---|---|

| T66~T70 | sections two and four: force-challenge confirmation, popup-log atomic commit, i18n fallback policy, and replay hard gates | forced challenge, explainability, UI summary exposure, and replay integrity stay closed under the same event-contract freeze |

| T71~T73 | sections three and four: diagnostic retention, audit fallback, and additive-only compatibility | security/privacy evidence and contract evolution remain hard-gated rather than descriptive only |

| T74~T79 | sections two and three: run-mode isolation, camp ordering, Boss pressure, objective pacing, reward draft, and AI-disable rule | engine entry packs stay tied to frozen runtime behavior rather than drifting into ad hoc scene logic |

| T80~T92 | section four: `A-001~A-020` are covered by executable hard gates | assertion integration packs and split gate runners remain release evidence, not informal test notes |

| T93~T100 | section three: start payload, camp slot model, one-action rule, and fatal camp-failure routing | startup, camp lifecycle, and fatal camp durability rules close as one deterministic runtime slice |

| T101~T103 | section three: Boss pressure includes round, difficulty, reveal delay stacking, and force-challenge cap | Boss profile, pressure resolver, and reveal-delay forcing remain one frozen pressure system |

| T104~T110 | sections three and four: event auto-trigger, objective publish-settle order, reward source routing, contract boundary, and content schema | board behavior, reward routing, DTO mapping, and content-pack governance stay aligned with landed contracts and gates |

| T111~T112 | section four plus `08-business-acceptance-scenarios.md`: business-flow closure and explainability/replay/i18n hard-gate closure | end-to-end acceptance evidence stays explicit, machine-routable, and semantically owned outside the routing page |



## Task-Family Closure Anchors (T121~T150)



| Task family | Checklist closure anchor | Closure meaning |

|---|---|---|

| T121~T122 | section three: start payload contains commander and strategem identity | commander roster gating and strategem selection stay inside start-config closure rather than drifting into UI-only state |

| T123~T124 | section two: runtime ordering fixed; replay ordering uses logical tick or round | camp -> pressure or Boss branch -> objective publish -> board phase remains deterministic and replay-stable |

| T125~T128 | section three: camp uses five building slots and building durability zero is permanent for the current run | camp durability model, persistence, and building-effect routing are closed by the same camp-building rule set |

| T129~T130 | section three: objectives do not publish after terminal endgame | camp durability fatal failure preempts later settlement branches and routes directly into defeat closure |

| T131~T136 | section three: Boss pressure includes round, difficulty, reveal delay stacking, and force-challenge cap | Boss profile, pressure math, reveal-delay stacking, and hard-cap forced challenge are frozen together |

| T137~T138 | section three: event tiles are auto-triggered; skip is not a normal escape path | event-tile enforcement and blocked-reason matrix close under one board-phase behavior rule |

| T139~T140 | section three: objectives publish and settle in the frozen order, and do not publish after terminal endgame | objective publish timing and terminal suppression remain one ordering contract |

| T141~T142 | section three: objective reward routing stays deterministic and reuses landed reward-offer compatibility constants until dedicated V3 reward-source contracts land | reward source integration and deterministic reward draft hook stay closed without inventing unlanded contracts |

| T143~T144 | section three: non-terminal Boss wins return to camp, final Boss victory ends the run, and camp-failure defeat remains terminal | endgame adjudication stays split cleanly between victory and camp-failure defeat branches |

| T145~T146 | section three: contracts stay under `Game.Core/Contracts`; UI does not branch on raw JSON | contract-set completion and HUD DTO mapping close under the same contract-boundary rule |

| T147~T148 | section three: content schema covers commander, strategem, camp building, Boss, and objective | schema extension and quality-gate closure are checked as one content-governance family |

| T149~T150 | section four plus `08-business-acceptance-scenarios.md`: business-flow closure is proven by deterministic scenario evidence | boss-win and camp-fail full-loop scenarios remain release-closure evidence tasks with an explicit semantic owner page |



## Task-Family Closure Anchors (T151~T175)



| Task family | Checklist closure anchor | Closure meaning |

|---|---|---|

| T151~T153 | section four plus `08-Contracts-Sanguo-GameLoop-Events.md`, `08-feature-slice-t2-monopoly-loop.md`, and `08-Contracts-Quality-Metrics.md` | core/UI hard-gate closure and R4 explainability-replay evidence remain executable with explicit semantic owner pages |

| T154 | sections two and four plus `08-Contracts-Security.md` | non-crash feedback suppression remains a security-governed release rule |

| T155 | section four plus `08-governance-freeze-change-control.md` | freeze revision, assertion update, and executable evidence update stay locked as one change-control triplet |

| T156~T157/T162~T163 | section four plus `08-Contracts-Sanguo-GameLoop-Events.md` and `08-governance-signal-compliance-workflow.md` | signal XML completeness, aggregation, and workflow wiring stay in one compliance lane with split semantic and execution owners |

| T158/T164/T165 | sections two and four plus `08-feature-slice-t2-monopoly-loop.md` | runtime signal subscription lifecycle remains leak-guarded under deterministic fixtures |

| T159~T160 | sections two and four plus `08-Contracts-Security.md` and `08-governance-logging-policy-and-lint.md` | privacy suppression and structured logging policy stay explicit and machine-linted |

| T161/T166~T168 | section four plus `08-governance-migration-compatibility.md` | migration report generation, completeness validation, and CI hard gate remain one governance family |

| T169~T170 | section three plus `08-Contracts-Sanguo-GameLoop-Events.md` | additive contract set and runtime-field harmonization remain contract-governed rather than gate-owned |

| T171~T172 | section three plus `08-contracts-taskmap-t50-t65.md` | compatibility constants and content-task mapping remain additive-only governance work |

| T173~T175 | section four plus the corresponding gate owner pages | replay, security-audit, and additive-only compatibility closure remain explicit stop-the-line bundles |

