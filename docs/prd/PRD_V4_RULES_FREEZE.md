# PRD V4 Rules Freeze (Combat Baseline)

## 0. Scope and Intent

- This document freezes the PRD v4 combat rule baseline.
- Scope: character attributes, enemy/Boss attributes, PVE combat simulation, combat result handling, and battle scene UI behavior.
- Any implementation that conflicts with this freeze must be treated as a bug unless superseded by a later freeze revision.

## 1. Reuse Constraints

- Reuse `SanguoCharacterDefinition` as the character schema extension point.
- Reuse `GameStartConfig` as the start-of-game contract surface.
- Reuse `SanguoCombatStarted` and `SanguoCombatEnded`; do not create parallel combat event names.
- Reuse `SanguoCombatResolver` as the combat resolution/simulation entry point.
- Reuse `SanguoBattleView.tscn` and `SanguoBattleView.cs` as the battle scene entry point.
- Keep `random_events.json` as a combat trigger source only; do not treat it as the formal enemy/Boss catalog.

## 2. Attribute Rules

### 2.1 Player Character Attributes

Player character combat attributes are:

- `MaxHP`
- `CurrentHP`
- `Attack`
- `CritRate`
- `CritMultiplier`
- `LifeStealRate`
- `DodgeRate`
- `AttackSpeed`
- `DamageReductionRate`
- `ReflectRate`
- `AoEEnabled`

`CombatRating` remains as a compatibility field and is not the v4 win/lose authority.

### 2.2 Enemy and Boss Attributes

Enemy and Boss combat attributes are:

- `MaxHP`
- `CurrentHP`
- `Attack`
- `LifeStealRate`
- `DodgeRate`
- `AttackSpeed`
- `DamageReductionRate`
- `ReflectRate`
- `AoEEnabled`

Enemy and Boss units do not use the crit system in this version.

### 2.3 Runtime Attribute Composition

Combat consumes runtime attributes, not raw initialization attributes.

Runtime attributes are computed once at battle initialization from:

1. Base
2. Growth
3. PassiveSkill
4. Treasure
5. Event
6. PreBattleBuff
7. PreBattleDebuff
8. Environment

Growth attributes are additive only. Buff/debuff effects are pre-battle modifiers in this version and do not dynamically change during combat.

## 3. Combat Timing Rules

- Combat is auto-attack gauge combat, not turn-based combat.
- `AttackSpeed` means seconds required per attack.
- `AttackSpeed` minimum is `0.5s`.
- A ready attack opportunity evaluates skills from highest `Priority` to lowest.
- Larger `Priority` value means higher priority.
- The first triggered skill consumes the attack opportunity.
- Normal attack is the final 100% fallback.

## 4. Simultaneous Ready Rules

When multiple units become ready at the same time, action order is:

1. Player main unit
2. Enemy/Boss main unit
3. Summons

If units are still tied at the same priority level with identical ready timing, use deterministic RNG to decide order.

## 5. Damage Rules

### 5.1 Direct Damage

- Normal attack base damage is `Attack`.
- Skill damage must use `Attack` as an input.
- Direct damage is affected by dodge, damage reduction, lifesteal, and reflect rules.
- Final direct damage minimum is `1`.

### 5.2 Dodge and Damage Reduction

- `DodgeRate` maximum is `0.90`.
- `DamageReductionRate` maximum is `0.90`.
- Percentage-derived values use floor rounding unless a later implementation note supersedes this.

### 5.3 Lifesteal

- Lifesteal applies only to direct damage.
- AoE lifesteal is calculated from total final direct damage across all affected targets.

### 5.4 Reflect

- Reflect is a special damage type.
- `ReflectRate = 0` means no reflect occurs.
- Reflect is not affected by dodge, damage reduction, or lifesteal.
- Reflect does not trigger reflect chains.
- If the defender is killed by the incoming hit, no reflect occurs from that defender.
- Reflect may kill the attacker.
- AoE reflect is applied per surviving target.

## 6. AoE Rules

- There is no `AoEValue`.
- AoE means targeting all alive units on the opposing side.
- AoE includes main unit and summons.
- Permanent AoE may come from passive skills or relics.
- Skill-triggered AoE is controlled by skill configuration.

## 7. Summon Rules

- Summons are independent combat units.
- Default summon generation uses 50% inheritable attributes and full HP based on 50% MaxHP.
- Default summon `AttackSpeed` is `2.0s`.
- Summons do not inherit crit, reflect, or permanent AoE.
- Summons have normal attack only by default.
- Single-target attacks prioritize opposing summons when any are alive.
- If multiple summons exist on the target side, choose one randomly.
- Main unit death ends combat immediately even if summons remain.

## 8. DoT Rules

- DoT is an independent damage type.
- DoT ticks every `1s`.
- DoT damage is independent from `Attack`.
- DoT cannot dodge, crit, lifesteal, or reflect.
- DoT is affected by damage reduction.
- DoT minimum final damage is `1`.
- Same-source DoT refreshes duration and overrides damage value.
- Same-source key is `SourceUnitId + DotEffectId`.
- Different-source DoTs coexist.
- If DoT tick and attack are due at the same time, DoT resolves first.
- If DoT kills a unit, that unit's pending attack is canceled.

## 9. Battle End Rules

- Combat ends immediately when either main unit reaches `CurrentHP <= 0`.
- Player main unit death means combat loss.
- Enemy/Boss main unit death means combat win.
- On loss, player returns to the map/main loop after report confirmation and HP is restored to 50% MaxHP.
- On win, player returns to the map/main loop after report and reward confirmation, and player HP remains at combat-end HP.

## 10. Battle Scene UI Rules

- Extend the existing `SanguoBattleView` scene.
- Display player/enemy names, model placeholders, runtime attributes, skills, passive skills, relics, and buff/debuff placeholders.
- Battle log shows the latest 15 entries.
- Result popup supports win/loss with a shared confirmation interaction.
- Reward popup supports multiple reward items.
- Pause freezes attack gauges, DoT timers, skill checks, animations, and log scrolling.
- Resume continues from the paused state without resetting timers.
- 2x speed changes time flow only; it must not change RNG order or probability results.

## 11. Data Rules

- Extend `characters.json`; keep `combatRating`.
- Add formal enemy/Boss catalogs instead of overloading `random_events.json`.
- Add minimal skill config for v4, while leaving room for a later skill engine.
- Extend `relics.json` additively with optional combat modifiers.
- Contract evolution must be additive unless a later migration plan explicitly changes the contract.

## 12. Change Control

Any rule change in sections 1-11 requires:

1. update this freeze file
2. update `PRD_V4_ACCEPTANCE_ASSERTIONS.md`
3. update `PRD_V4_TRACEABILITY_MATRIX.md`
4. provide matching implementation or task evidence
