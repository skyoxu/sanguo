# PRD V4 Acceptance Assertions (Combat)

## 0. Purpose

- This file defines machine-checkable assertions for `PRD_V4_RULES_FREEZE.md`.
- Assertion IDs are stable references for tasks, tests, CI checks, and review evidence.

## 1. Core Assertions

### V4-A-001 Reuse Existing Combat Surface

- Given v4 combat implementation work starts,
- When combat contracts and UI are updated,
- Then existing `SanguoCombatStarted`, `SanguoCombatEnded`, `SanguoCombatResolver`, and `SanguoBattleView` remain the primary surfaces.
- Evidence: contract inspection + scene path inspection.

### V4-A-002 CombatRating Compatibility

- Given character data is loaded,
- When v4 combat fields are present,
- Then `CombatRating` remains available and is not removed or renamed.
- Evidence: character catalog loader test.

### V4-A-003 Runtime Attribute Snapshot

- Given battle initialization starts,
- When player and enemy/Boss units are created,
- Then combat uses final runtime attributes, not raw base attributes alone.
- Evidence: runtime attribute aggregation unit test.

### V4-A-004 AttackSpeed Semantics

- Given a unit has `AttackSpeed = X`,
- When combat simulation advances,
- Then the unit attacks after X seconds of gauge time.
- And `AttackSpeed` is clamped to minimum `0.5s`.
- Evidence: deterministic combat timing unit test.

### V4-A-005 Skill Priority Trigger Chain

- Given multiple skills with different priorities and trigger chances,
- When a unit attack opportunity occurs,
- Then skills are checked from highest priority to lowest.
- And the first triggered skill consumes the attack opportunity.
- Evidence: seeded skill trigger unit test.

### V4-A-006 Normal Attack Fallback

- Given no configured skill triggers,
- When a unit attack opportunity occurs,
- Then normal attack triggers as the 100% fallback.
- Evidence: combat resolver unit test.

### V4-A-007 Simultaneous Ready Ordering

- Given player, enemy/Boss, and summon units become ready at the same time,
- When action ordering is resolved,
- Then player main unit acts before enemy/Boss main unit, and enemy/Boss main unit acts before summons.
- Evidence: same-tick combat ordering unit test.

### V4-A-008 Direct Damage Minimum

- Given direct damage calculation produces a positive value below 1 after mitigation,
- When damage is applied,
- Then final direct damage is 1.
- Evidence: damage formula unit test.

### V4-A-009 Dodge and Damage Reduction Caps

- Given `DodgeRate` or `DamageReductionRate` exceeds allowed cap,
- When runtime attributes are computed,
- Then each is capped at `0.90`.
- Evidence: attribute clamp unit test.

### V4-A-010 Lifesteal Direct Damage Only

- Given direct damage and non-direct damage occur,
- When lifesteal is calculated,
- Then only direct damage contributes to lifesteal.
- Evidence: damage-type unit test.

### V4-A-011 Reflect Rules

- Given reflect is configured,
- When direct damage hits a surviving defender,
- Then reflect applies as special damage and does not chain.
- And if the defender dies from the hit, no reflect is emitted from that defender.
- Evidence: reflect branch unit test.

### V4-A-012 AoE Targets All Alive Opposing Units

- Given AoE damage is triggered,
- When the opposing side has a main unit and summons alive,
- Then all alive opposing units are targeted.
- Evidence: AoE target selection unit test.

### V4-A-013 Summon Target Priority

- Given the target side has one or more summons alive,
- When a single-target attack selects a target,
- Then a summon is selected before the main unit.
- Evidence: seeded target selection unit test.

### V4-A-014 Summon Inheritance Boundary

- Given a summon is created,
- When summon runtime stats are computed,
- Then it uses 50% inheritable attributes and does not inherit crit, reflect, or permanent AoE.
- Evidence: summon creation unit test.

### V4-A-015 DoT Timing and Damage Type

- Given DoT is active,
- When its tick time arrives,
- Then it deals independent damage, cannot dodge/crit/lifesteal/reflect, is affected by damage reduction, and has minimum final damage 1.
- Evidence: DoT unit test.

### V4-A-016 DoT Before Same-Time Attack

- Given DoT tick and attack are due at the same simulation time,
- When combat advances,
- Then DoT resolves first.
- And if DoT kills the unit, the pending attack is canceled.
- Evidence: same-time DoT ordering unit test.

### V4-A-017 Battle End on Main Unit Death

- Given any main unit reaches `CurrentHP <= 0`,
- When combat simulation resolves the event,
- Then battle ends immediately even if summons remain alive.
- Evidence: battle end unit test.

### V4-A-018 Loss Recovery HP

- Given player loses combat,
- When battle report is confirmed,
- Then map/main-loop return occurs and player HP is restored to 50% MaxHP.
- Evidence: combat result application test.

### V4-A-019 Win Keeps Remaining HP

- Given player wins combat,
- When battle report and reward are confirmed,
- Then map/main-loop return occurs and player HP remains at combat-end HP.
- Evidence: combat result application test.

### V4-A-019A Savegame Overwrite Cross-Restart Assertion Mapping

- Requirement: `REQ-e59441a62b3c` (source: `docs/prd/PRD_V4_RULES_FREEZE.md:186`).
- Given savegame slot `(uid, slot=1)` already has persisted payload,
- When the same slot is upserted after reopen/restart,
- Then the latest payload must overwrite the previous payload for that slot.
- And cross-restart read consistency must return the latest payload only.
- Observable assertions must cover:
  - open success
  - overwrite persistence
  - cross-restart read consistency
- Test mapping: `Tests.Godot/tests/Adapters/Db/test_savegame_update_overwrite_cross_restart.gd`
- Acceptance anchor mapping: `ACC:T183.1`, `ACC:T183.2`, `ACC:T183.3`, `ACC:T183.4`.
- Evidence: deterministic GdUnit test assertions and acceptance anchor tracing.

### V4-A-020 Battle UI Required Elements

- Given `SanguoBattleView` loads,
- When v4 battle scene is initialized,
- Then player/enemy panels, attributes, skills, passive skills, relics, log, pause/resume, 2x speed, and result/reward UI are available.
- Evidence: GdUnit scene structure test.

### V4-A-021 Battle Log Fixed Window

- Given more than 15 combat log entries exist,
- When the battle log renders,
- Then only the latest 15 entries are visible.
- Evidence: UI log rendering test.

### V4-A-022 Pause Freezes Simulation

- Given combat is running,
- When pause is activated,
- Then attack gauges, DoT timers, skill checks, animations, and log scrolling freeze.
- Evidence: scene integration test.

### V4-A-023 Two Times Speed Determinism

- Given the same battle seed and configuration,
- When combat runs at 1x and 2x,
- Then probability outcomes and event order remain deterministic.
- Evidence: deterministic replay-style combat test.

### V4-A-024 Additive Contract Evolution

- Given v4 combat contracts are expanded,
- When compatibility checks run,
- Then existing event names remain unchanged and contract changes are additive.
- Evidence: contract compatibility test.

## 2. CI Hook Recommendations

- Hook 1: Core combat simulation unit suite (`V4-A-003` to `V4-A-019`) as hard gate.
- Hook 2: contract compatibility suite (`V4-A-001`, `V4-A-002`, `V4-A-024`) as hard gate.
- Hook 3: Godot battle scene suite (`V4-A-020` to `V4-A-023`) as UI/glue gate.

## 3. Evidence Layout Suggestion

- `logs/ci/<date>/assertions/prd-v4-combat-core.json`
- `logs/ci/<date>/assertions/prd-v4-contracts.json`
- `logs/ci/<date>/assertions/prd-v4-battle-ui.json`

Each summary should include:

- assertion id
- status (pass/fail/skip)
- evidence file path
- failure reason
