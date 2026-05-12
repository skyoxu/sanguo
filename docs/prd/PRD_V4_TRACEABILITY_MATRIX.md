# PRD V4 Traceability Matrix and Combat Blueprint

- Date: 2026-05-11
- Inputs: `docs/prd/prd_v4.md`, current repository code and data
- Scope: character attributes, enemy/Boss attributes, PVE combat logic, battle scene UI

## 1. Requirement Traceability

Status legend:

- Implemented: stable code path + test evidence already exists.
- Partial: base capability exists but does not yet meet PRD v4 target.
- Gap: implementation missing and must be added in this phase.

| ReqID | PRD v4 requirement | Status | Code evidence | Test evidence | Assessment |
|---|---|---|---|---|---|
| V4-R1 | Extend character combat attributes while keeping `CombatRating` | Gap | `Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs` | Existing character loader tests should be extended | Character schema currently only exposes `CombatRating` for combat. |
| V4-R2 | Add formal enemy and Boss combat catalogs | Gap | `Data/random_events.json` | No dedicated enemy/Boss catalog tests yet | Random events only provide `encounterId` and `encounterTarget`; formal enemy/Boss definitions are missing. |
| V4-R3 | Add minimal skill config surface | Gap | No `Data/skills.json` yet | No skill catalog tests yet | Current demo strategems are not a formal combat skill catalog. |
| V4-R4 | Extend relics with optional combat modifiers | Partial | `Data/relics.json` | Existing relic tests should be extended | Relics exist, but only economy effects are present. |
| V4-R5 | Compute runtime combat attributes at battle initialization | Gap | `Game.Core/Services/Sanguo/SanguoCombatResolver.cs` | No runtime stat aggregation tests yet | Existing resolver uses threshold comparison instead of runtime stats. |
| V4-R6 | Replace threshold combat with auto-attack combat simulation | Gap | `Game.Core/Services/Sanguo/SanguoCombatResolver.cs` | Existing Task59 combat tests should be rewritten/extended | Current logic is `combatRating >= encounterTarget`. |
| V4-R7 | Support skill priority trigger chain and normal attack fallback | Gap | `Game.Core/Services/Sanguo/SanguoCombatResolver.cs` | No skill trigger tests yet | Needs deterministic seeded simulation tests. |
| V4-R8 | Support AoE, summons, reflect, lifesteal, and DoT | Gap | `Game.Core/Services/Sanguo/SanguoCombatResolver.cs` | No damage-type tests yet | All core combat branches are new v4 behavior. |
| V4-R9 | Extend combat contracts additively | Partial | `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs` | Existing combat event tests should be extended | Started/ended events exist, but payload is minimal. |
| V4-R10 | Expand `SanguoBattleView` into real battle scene | Partial | `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn`, `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs` | Existing UI/Godot tests should be extended | Scene exists but only shows started/result text and continue button. |
| V4-R11 | Preserve map/main-loop return behavior after combat | Partial | `Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs`, `Game.Core/Services/Sanguo/SanguoCombatResolver.cs` | Task59-style tests should be extended | Combat branch exists; v4 win/loss HP and reward behavior is not implemented. |
| V4-R12 | Keep v4 changes additive and aligned with existing surfaces | Partial | `Game.Core/Contracts/Sanguo/**`, `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn` | Contract compatibility tests needed | Existing surfaces are reusable; implementation must avoid parallel systems. |

## 2. Existing Reusable Surfaces

1. Character schema and loader
   - `Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs`
   - `Game.Core/Services/Sanguo/SanguoCharactersCatalogLoader.cs`
   - `Data/characters.json`

2. Combat contract and resolver
   - `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs`
   - `Game.Core/Services/Sanguo/SanguoCombatResolver.cs`

3. Battle UI scene
   - `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn`
   - `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs`

4. Existing trigger and reward-adjacent data
   - `Data/random_events.json`
   - `Data/relics.json`

5. Start config
   - `Game.Core/Contracts/Sanguo/GameStartConfig.cs`

## 3. New or Extended Artifacts Needed

### 3.1 Extend Existing

- `Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs`
- `Game.Core/Services/Sanguo/SanguoCharactersCatalogLoader.cs`
- `Data/characters.json`
- `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs`
- `Game.Core/Services/Sanguo/SanguoCombatResolver.cs`
- `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn`
- `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs`
- `Data/relics.json`

### 3.2 Add New

- `Data/enemies.json`
- `Data/bosses.json`
- `Data/skills.json`
- Enemy/Boss catalog loader in `Game.Core/Services/Sanguo/**`
- Skill catalog loader in `Game.Core/Services/Sanguo/**`
- Combat runtime stat and simulation model under `Game.Core/**`

## 4. High-Risk Contradictions

1. `CombatRating` vs runtime attributes
   - Risk: old threshold logic may remain active and conflict with v4 simulation.
   - Required handling: keep `CombatRating` as compatibility summary only; route v4 combat through runtime stats.

2. `random_events.json` as trigger vs enemy catalog
   - Risk: event data becomes overloaded as formal enemy config.
   - Required handling: keep event trigger data separate from enemy/Boss catalogs.

3. Battle scene as popup vs real combat scene
   - Risk: `SanguoBattleView` remains a result popup while Core assumes live simulation presentation.
   - Required handling: evolve the existing scene in place with required battle UI nodes.

4. Temporary strategems vs future skill engine
   - Risk: demo active/passive strategems drift into a second skill model.
   - Required handling: use v4 minimal `skills.json` only as transitional config and leave engine migration room.

## 5. Recommended Implementation Order

1. Contract and data model expansion
   - character fields
   - combat result payload
   - enemy/Boss/skill/relic data fields

2. Deterministic Core combat simulation
   - runtime stat aggregation
   - attack gauge
   - priority skill trigger
   - damage types
   - battle end/result payload

3. Battle scene integration
   - `SanguoBattleView` node expansion
   - log/result/reward UI
   - pause/resume/2x behavior

4. Main loop and event trigger connection
   - map/event combat trigger to enemy/Boss config
   - result application to player HP, rewards, and map return

## 6. Test Blueprint

- Core xUnit: runtime stat aggregation, attack timing, skill priority, normal fallback, damage types, summons, DoT, reflect, battle end.
- Contract tests: additive combat contract changes, unchanged event names, character schema compatibility.
- Loader tests: `characters.json`, `enemies.json`, `bosses.json`, `skills.json`, `relics.json`.
- GdUnit tests: `SanguoBattleView` node availability, log fixed window, pause freeze, 2x deterministic display behavior.

## 7. Chapter 3 and Chapter 4 Notes

- Chapter 3 should consume all PRD v4 files as the same requirement source set.
- Chapter 4 should decide contract changes from `PRD_V4_RULES_FREEZE.md` and `PRD_V4_TRACEABILITY_MATRIX.md`.
- Contract changes are expected, but they should be additive and preserve existing event names.
