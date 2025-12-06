# Signals Contract Guidelines (ADR-0022)

- Naming: snake_case (e.g., `player_died`, `score_updated`).
- Payloads: document fields and types; avoid Godot-specific types in domain events.
- Ownership: declare which node/autoload emits the signal.
- Versioning: changes must be referenced in ADR-0022 update notes.

Examples
- Node signal: `player_died(health:int, position:Vector2)`
- Global bus (autoload): `app.game_state_changed(state:String)`

