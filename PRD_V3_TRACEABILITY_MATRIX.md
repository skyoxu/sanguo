# PRD v3 Traceability Matrix and Engine Blueprint

- Date: 2026-03-11
- Inputs: `prd_v3.md`, `CURRENT_STAGE_FOR_BMAD.md`, code and tests
- Scope: P0/P1 only

## 1) Requirement Traceability (P0/P1)

Status legend:
- Implemented: stable code path + test evidence
- Partial: base capability exists but not yet meeting PRD v3 target
- Gap: key implementation missing and must be added in this phase

| ReqID | PRD v3 requirement | Status | Code evidence | Test evidence | Assessment |
|---|---|---|---|---|---|
| R1 | Campaign mode entry and start config | Partial | `Game.Core/Contracts/Sanguo/GameStartConfig.cs:16` | `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs:17` | Start config exists; missing explicit `RunMode=Campaign` and campaign-only fields. |
| R2 | Fixed round order: camp -> pressure -> board -> return to camp | Partial | `Game.Core/Services/SanguoTurnManager.cs:2358`, `Game.Core/Services/SanguoTurnManager.cs:2520` | `Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs:15`, `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs:22` | Global-event timing exists; no dedicated camp phase state machine. |
| R3 | New win/lose loop: kill final Boss / camp HP zero | Gap | `Game.Core/Services/SanguoTurnManager.cs:652`, `Game.Core/Contracts/Sanguo/GameEvents.cs:167` | `Game.Core.Tests/Tasks/Task60GameEndEventContractTests.cs:16` | End reasons still old-rule oriented (elimination/bankrupt), not Boss/camp based. |
| R4 | End-to-end explainability and replayability | Implemented | `Game.Godot/Scripts/UI/HudEventDtoMapper.cs:7`, `Game.Godot/Scripts/UI/EventExplainService.cs:16`, `Game.Godot/Scripts/UI/HUD.cs:17` | `Tests.Godot/tests/UI/test_event_log_summary_localized.gd:1` | Existing explain chain can carry new campaign events. |
| R5 | Camp system: 5 building HP pools, one action per round | Gap | `Game.Core/Contracts/Sanguo/SanguoBuildingDefinition.cs:1`, `Game.Core/Services/SanguoTurnManager.cs:1336` | `Game.Core.Tests/Tasks/Task64RegionsTests.cs:14` | City building upgrade exists; camp HP/action system not present yet. |
| R6 | Boss dice pressure engine | Gap | `Game.Core/Services/SanguoTurnManager.cs:2358`, `Game.Core/Services/SanguoGlobalEventRoundGate.cs:8` | `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs:22` | Round gate exists; no Boss dice model and pressure settlement pipeline. |
| R7 | Board/combat extension with trigger-skip-return | Implemented | `Game.Core/Services/Sanguo/SanguoCombatResolver.cs:6`, `Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs:27` | `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs:16` | Reuse current branch; avoid combat engine rewrite. |
| R8 | Main quest minimum loop with chain unlock | Gap | `Game.Core/Services/SanguoTurnManager.cs:13` | No dedicated Task-level test found | No quest-chain engine observed in current codebase. |
| R9 | Contract naming and data-driven constraints | Implemented | `Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs:75`, `Game.Core/Services/Sanguo/SanguoContentPackResolver.cs:24` | `Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs:15` | Contract + content-pack pipeline is reusable. |
| R10 | AI should be disable-by-default for campaign | Partial | `Game.Core/Services/SanguoAiDeterministicDecisionApi.cs:10`, `Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs:242` | `Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs:18` | AI capability is solid; campaign default-off switch is not explicit yet. |
| R11 | Non-functional hard gates (coverage/smoke/audit) | Implemented | `scripts/python/quality_gates.py:221`, `scripts/python/check_architecture_hotspots.py:40` | `Game.Core.Tests/Tasks/Task47QualityGatesBehaviorTests.cs:13`, `Game.Core.Tests/Tasks/Task47QualityGatesArchitectureHotspotsTests.cs:12` | Quality baseline is ready for extension. |

## 2) High-Risk Contradictions

1. Task-state vs code reality mismatch (P1)
   - Deferred in SSOT: `.taskmaster/tasks/tasks.json:1874`, `.taskmaster/tasks/tasks.json:1902`, `.taskmaster/tasks/tasks.json:1927`, `.taskmaster/tasks/tasks.json:1955`
   - But code/tests already exist: `Game.Core.Tests/Tasks/Task62RelicsTests.cs:18`, `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs:22`, `Game.Core.Tests/Tasks/Task64RegionsTests.cs:14`, `Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs:15`
   - Impact: task decomposition may duplicate or regress existing behavior.

2. No RunMode isolation for campaign rules yet (P0)
   - Existing game-end flow remains old-rule driven: `Game.Core/Services/SanguoTurnManager.cs:652`
   - Impact: direct feature stacking will likely create state-machine conflicts.

## 3) Existing Engine-Like Modules (7)

Engine criterion: cross-phase orchestration modules that own game rules/state transitions.

1. Turn Loop Engine
   - `Game.Core/Services/SanguoTurnManager.cs:13`
   - `Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs:27`

2. Economy Engine
   - `Game.Core/Services/SanguoEconomyManager.cs:25`

3. Event Bus Engine
   - `Game.Core/Services/EventBus.cs:12`

4. AI Decision Engine
   - `Game.Core/Services/SanguoAiDeterministicDecisionApi.cs:10`
   - `Game.Core/Services/DefaultSanguoAiDecisionPolicy.cs:5`

5. Combat Resolve Engine
   - `Game.Core/Services/Sanguo/SanguoCombatResolver.cs:6`

6. Content Pack Engine
   - `Game.Core/Services/Sanguo/SanguoContentPackResolver.cs:24`
   - Catalog loaders already wired for maps/events/cards/buildings/relics/regions.

7. Explainability Engine (UI)
   - `Game.Godot/Scripts/UI/HudEventDtoMapper.cs:7`
   - `Game.Godot/Scripts/UI/EventExplainService.cs:16`

## 4) Engines Needed by PRD v3

### P0 (must build first)

1. CampaignRuleEngine (new)
   - Responsibility: run-mode split, campaign win/lose criteria, campaign lifecycle boundaries.
   - Hook: game-end branch inside turn loop.

2. CampLifecycleEngine (new)
   - Responsibility: camp phase state machine, camp building HP and one-action-per-round policy.
   - Hook: round transition before/after board phase.

3. BossPressureEngine (new)
   - Responsibility: boss-dice roll and pressure settlement (elite pressure + global debuffs).
   - Hook: existing global round gate timing.

### P1 (next)

4. StrategemEngine (new)
   - Responsibility: active/passive strategy logic and pouch resource progression.
   - Constraint: keep separate from ActionCard inventory semantics.

5. RandomObjectiveEngine (new)
   - Responsibility: per-round random objective generation and reward settlement for pace compensation.
   - Constraint: data-driven only, no UI hardcoding.

6. RewardDraftEngine (new, minimal)
   - Responsibility: deterministic 3-choice reward drafting for camp/battle outcomes.

## 5) Recommended Next Step

1. Build `RunMode + CampaignRuleEngine` first to avoid state collision.
2. Reconcile SSOT task statuses vs already-implemented code before new task slicing.
3. Execute in this order: CampaignRuleEngine -> CampLifecycleEngine -> BossPressureEngine -> StrategemEngine -> RandomObjectiveEngine.

## 6) Clarified Rule Baseline (Round 1-3 Confirmed)

### 6.1 Core mode and win lose

- [1-1] Campaign entry via dedicated main menu button.
- [2-1] Final Boss kill triggers immediate victory.
- [3-3] Lose only when all camp buildings reach zero HP.
- [9-2] AI is forced off in campaign mode for this phase.
- [10-1] Save load mode or version mismatch is hard fail.

### 6.2 Round flow and pressure

- [5-3] Boss dice uses base value plus modifiers from systems like buildings or strategems.
- [6-1 revised] Non-Boss pressure effects are single-round by default; Boss-reveal pressure is persistent until the current Boss is defeated.
- [7-2] Unresolved elite pressure damage settles at camp phase start.
- [17-1] Camp phase order: settle previous pressure damage first, then choose one camp function.
- [18-1] Final Boss is revealed immediately when the configured round is reached.

### 6.3 Combat and Boss challenge boundaries

- [8-2] Combat loss returns to camp and unit strength is reset to 1.
- [19-1] Boss can be challenged repeatedly after reveal.
- [29-custom] Boss challenge is only available in camp phase and never in board phase.
- [29-custom] Final Boss win ends the run immediately.
- [29-custom] Any Boss loss returns to camp with unit strength reset to 1.
- [29-custom] Non final Boss win grants reward and returns to camp, run continues.
- [29-custom] Player may delay Boss challenge across rounds, and pressure increases each delayed round.

### 6.4 Strategem and random objective rules

- [13-1] Active strategem can only be used in BeforeRoll window.
- [14-1] Active strategem usage is fixed to once per round.
- [15-1] Passive strategem is always on.
- [11-3 rename] No quest chain in this phase. Use per round random objectives.
- [12-clarified] Random objective purpose is pace compensation to reduce stall behavior for rewards.

### 6.5 Reward and content constraints

- [16-1] Three choice reward options cannot repeat within the same draft.
- [20-1 revised] Action result popup is blocking; normal result popup may timeout auto-close, while critical popup requires manual confirmation.
- [21-1] Random objective refreshes every round and expires if not completed in that round.
- [22-1] Objective type in phase one: reach camp this round.
- [23-3] Reward pool includes money, recovery, temporary multipliers, and card or relic options.
- [24-1] Objective failure has no penalty and only misses reward.

### 6.6 Pressure scaling and durability

- [25-3 revised] Delaying Boss challenge increases Boss pressure each round; delay-round hard cap and pressure-growth cap are tracked separately.
- [26-3 revised] Pressure-growth cap is difficulty based: normal 5, hard 8, hell 12.
- [27-1] Camp building initial HP is 4 each.
- [28-1] Camp buildings are repairable, and at most one building can be repaired per round.

### 6.7 Versioning hard gate accepted option 30-1

- [30-1] Any gameplay impacting campaign content change must bump pack version as a hard CI gate.
- Save header must include content_fingerprint in addition to packId and packVersion.
- Mismatch blocks load continuation and writes structured audit evidence.

### 6.8 Additional clarified boundaries (31-50)

- [31-1] Boss delay counter resets only when current Boss is defeated.
- [32-custom] Reveal is executed before force-challenge decision; no challenge before reveal.
- [34-2] Reward draft must still show 3 options; fill with guaranteed fallback options when dedup leaves fewer than 3.
- [35-custom] Cards may duplicate; relics must redraw, and fallback to gold when relic pool is exhausted.
- [36-1] Hard load rejection shows popup and stays on main menu.
- [37-2] `content_fingerprint` covers all gameplay-impacting configuration files.
- [38-1] Player manually selects repair target.
- [39-1] Repair consumes the one camp action of that round.
- [40-1] Campaign mode rejects incompatible saves as hard-fail.
- [41-1] Delay pressure escalation starts from the round after reveal.
- [42-1] After reaching escalation cap, growth stops (no extra conversion rule).
- [43-2] Relic reward probability is difficulty-tiered and config-driven.
- [44-1] No reward decay due to Boss delay.
- [45-1] Repair is free.
- [46-3] Repair amount scales by building level.
- [47-2] In camp phase, player can use one camp action then choose Boss challenge.
- [48-1] No lose-streak protection for Boss challenges.
- [49-1] Hard load rejection must emit audit evidence.
- [50-1] Player-facing message is generic incompatibility text.

### 6.9 Additional clarified boundaries (51-100)

- [51-2] `RoundNumber` is mandatory only for round-related events.
- [52-1] Split Boss events: reveal and challenge-start are separate.
- [53-1] Random objective events must include `assigned/completed/expired`.
- [54-1] Camp building events include `damaged/repaired/function.used`.
- [55-1] Add dedicated rejection event `core.sanguo.save.load.rejected`.
- [56-1] Test order: Core xUnit first, then GdUnit wiring tests.
- [59-1] New campaign logic must be extracted to dedicated engine classes (no further growth in TurnManager for those rules).
- [61-custom] Duration target by difficulty: normal 45-60 minutes (2 Bosses), hard/hell 60-90 minutes (3 Bosses).
- [62-custom] Boss delay hard cap is 10 rounds.
- [63-1] Reaching delay cap forces Boss challenge on next leave-camp transition.
- [66-custom] Building HP <= 0 is permanent loss for that building: no repair, function permanently disabled.
- [69-1][92-1] At most one relic option can appear in one reward draft.
- [71-custom] If force-challenge is active, leaving camp triggers Boss fight immediately.
- [72-2][109-1] Exit is allowed but marks `forced_challenge_pending`.
- [74-custom] Camp HP settlement is first priority in camp phase; `<=0` triggers immediate fail settlement.
- [75-2 revised] Previous-round objective is settled at camp entry before Boss challenge checks; current-round objective is published only after Boss settlement.
- [76-2][88-3] Card duplication uses per-card cap from config.
- [77-2][94-1] Gold fallback for relic exhaustion is difficulty-tiered (normal 100, hard 150, hell 200).
- [79-1] After Boss-loss reset to 1 strength, autosave is triggered immediately.
- [81-2] Delay counter starts as 1 on reveal round.
- [82-1] Delay counter reset happens only on Boss defeat.
- [83-1] Delay counters are isolated per Boss (no inheritance).
- [84-1] No second forced challenge in a round if player already challenged once.
- [85-1][129-1] Reward is applied before autosave.
- [86-1][122-2] Autosave failure warns and continues; first popup then same-round failures become silent+audited.
- [87-1] After Boss-loss return, cannot re-challenge again in the same round.
- [95-2][96-1] Reward is never empty and must include at least gold.
- [97-1][124-2] RNG reproducibility requires seed + substream step counters.
- [98-2] Probability evidence logs include hit result and sampled random value.
- [99-2 revised] Autosave uses dedicated autosave channel (separate from manual save slots) and follows single overwrite policy.

### 6.10 Additional clarified boundaries (101-169)

- [101-1] Reward probability config path: `Data/packs/<pack>/balance/reward_probabilities.json`.
- [102-1] Probability config changes apply to new runs only.
- [103-1] Fingerprint algorithm is SHA-256.
- [104-1] Fingerprint scope is gameplay-impacting files only.
- [105-1] Missing required config fields cause hard-fail (block start/load).
- [106-1] Hard load rejection does not break current active run context.
- [107-1] `save.load.rejected` must include reason and expected/actual pack/version fields.
- [108-1] Critical popups require manual confirmation (no auto-close).
- [111-1] TurnManager is orchestrator-only for campaign rules; CampaignRuleEngine owns campaign logic.
- [112-1] CampLifecycleEngine uses independent state object.
- [113-1] BossPressureEngine outputs structured DTO + events.
- [114-1] Random objective refresh happens at configured step 7.
- [115-3] Strategem resource source is mixed: config first, constant fallback.
- [116-1] Reward candidates are configuration-driven with rule filtering.
- [117-1] Event naming follows `core.sanguo.<domain>.<action>`.
- [118-custom] Engine build order: Campaign -> Camp -> BossPressure -> Strategem -> RandomObjective -> RewardDraft.
- [119-1] Minimum test gate per engine: 5 Core tests + 1 contract test + 1 UI wiring test.
- [121-1] Autosave uses single overwrite slot policy.
- [123-2] Load picks latest autosave that passes validation.
- [125-3] `forced_challenge_pending` clears after Boss battle settlement (win or loss).
- [126-3] Reward card overflow handling: redraw valid candidate, then fallback gold if exhausted.
- [127-2] Blocking popup provides secondary \"view log and continue\" action.
- [128-2] Introduce and validate round sequence numbers for event ordering.
- [131-1] `sequence_no` scope is per-round incremental counter.
- [132-2] `sequence_no` validation failure raises soft UI warning and audit.
- [133-2] Boss pressure event payload includes total + source breakdown.
- [134-2] Objective expiration includes reason codes.
- [135-3] Reward draft event records both pre-filter and post-filter candidate snapshots.
- [136-2] Save audit records both success and failure.
- [137-1] No exception path for repairing permanently destroyed buildings in this phase.
- [138-2] Boss challenge confirm popup shows pressure summary and failure consequence summary.
- [139-1] Rule/config errors show player-friendly message with error code.
- [141-1][142-1][143-2] Difficulty profiles are centralized config; selected at run start; minimal diff includes pressure cap, reward probability, and Boss dice base.
- [144-2][145-1][146-2][147-3] Balance regression: run on data changes; fixed-seed batch mode with N=50; soft on PR and hard on protected branch.
- [148-1][149-1] Rule changes require doc-first update and minor version bump by default.
- [151-2][152-2][153-2] Delivery gate: M1 requires Core + minimal UI wiring including camp panel; M2 requires M1 plus balance gate green.
- [154-2][155-2][156-2][157-1] Implementation governance: contract diff checklist required; split by rule-test-wire triplet; target <=8 files and 0.5-1 day per task.
- [158-2][159-2] Only P0/P1 changes may interrupt flow; add soft consistency gate for frozen-rule document hash.
- [161-2][162-1][163-1] Release strategy: campaign mode enabled by default; rollback prefers config rollback first.
- [164-3][165-2][166-2][167-1][168-2][169-1] Rollback/ops baseline: migration-first compatibility strategy, pre-release gates include quality+balance, monitor 48h, any P0 triggers rollback, duty owner executes, freeze label `Campaign-Rules-v1.0`.

### 6.11 New hard guard agreed after deep clarification

- Normal difficulty hard target is fixed to 45-60 minutes with 2 Bosses.
- Hard and hell target range is 60-90 minutes with 3 Bosses.
- Add high-pressure threshold warning when normal difficulty progression stalls beyond configured round threshold.
- Minimum replay evidence per round is fixed (run/round id, boss state, pressure totals and breakdown, objective result, camp HP, reward draft result, player power snapshot, RNG trace, content fingerprint).

### 6.12 Immutable round timeline rules (camp, Boss, objective)

- Reaching camp closes and settles the previous round random objective immediately.
- A new round begins at camp phase and increments `round_no`.
- Leaving camp may trigger Boss challenge based on current rules; that Boss challenge is part of the same new round.
- After Boss battle settlement, publish the new random objective, and its validity window is the remaining board phase of that round.
- If Boss battle directly ends the run (victory or fail), no new random objective is published for that round.
