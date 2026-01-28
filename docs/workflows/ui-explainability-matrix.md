# UI Explainability Matrix (HUD Event Log)

## Scope
- Applies to HUD EventToast, EventLogPanel, and EventExplainService.
- Facts only: no inference, no rule computation, no hidden adjustments.
- Event naming follows ADR-0004, i18n follows ADR-0010.

## Event Coverage Matrix
| EventType | Toast Summary (facts) | Log Summary (facts) | Details: Facts | Details: Deltas | Notes |
| --- | --- | --- | --- | --- | --- |
| core.sanguo.city.toll.paid | payer, owner, city, amount, owner_amount, overflow | same as toast | game_id, turn, city_id, payer_id, owner_id, applied_multipliers | money_delta[payer], money_delta[owner], treasury_delta | overflow only when nonzero |
| core.sanguo.economy.month.settled | turn, year, month | same as toast | game_id, turn, year, month, player_settlements_count, applied_multipliers | money_delta per player, truncated after 12 | no aggregation in UI |
| core.sanguo.board.token.moved | player, from, to, steps, passed_start | same as toast | game_id, player_id, steps, passed_start, from_index, to_index, tile labels when available | none | tile labels are best effort |
| core.sanguo.random_event.applied | prompt_message, player, picked_id or event_id, effect_kind, trigger_source, trigger_round, money_delta/step_delta, next_step | same as toast | game_id, player_id, event_id, picked_id, effect_kind, encounter_id, encounter_target, prompt_message, trigger_source, trigger_round, next_step, applied_multipliers | money_delta, step_delta | do not infer outcome |
| core.sanguo.loot.granted | player, loot_kind, card/relic, money_delta, source_kind/source_id | same as toast | game_id, player_id, loot_kind, card_id, relic_id, source_kind, source_id | money_delta | facts only |
| core.sanguo.relic.applied | player, relic_id, effect_kind, money_delta/step_delta | same as toast | game_id, player_id, relic_id, effect_kind | money_delta, step_delta | facts only |
| core.sanguo.game.ended | end_reason, winner_player_id | same as toast | game_id, end_reason, winner_player_id | none | echo only |

| core.sanguo.economy.season.event.applied | year, season, yield_multiplier | same as toast | game_id, turn, year, season, yield_multiplier, affected_regions_count, applied_multipliers | none | facts only |
| core.sanguo.economy.year.price.adjusted | city, year, old_price, new_price | same as toast | game_id, turn, year, city_id, old_price, new_price, applied_multipliers | none | price snapshot |
| core.sanguo.city.toll.synergy.paid | payer, owner, landing_city, paid_total, cities | same as toast | game_id, turn, payer_id, owner_id, landing_city_id, region_id, expected_total_amount, paid_total_amount, expected/paid cities count | none | includes breakdown amounts and multiplier snapshots |
### Generic Fallback
- If event type is not in the matrix, use generic summary and basic facts: game_id, turn, round, player_id, active_player_id, applied_multipliers.
- Never drop the event due to missing optional fields. Emit a minimal summary and details block.

## i18n Rules (Minimum)
- Translation resources live under Game.Godot/Translations/ and are loaded by LocalizationBootstrap and SettingsLoader.
- Key format for event specific text:
  - ui.hud.event.<event_type>.title
  - ui.hud.event.<event_type>.summary
  - ui.hud.event.<event_type>.detail.<field>
  - ui.hud.event.<event_type>.delta.<field>
- Field keys use snake_case names shown in the details list, for example money_delta, player_id, city_id, turn.
- Missing i18n keys must fall back to raw key and raw payload values. Do not show empty strings.

## Update Checklist
1) Add or update the EventExplainService branch for the new event.
2) Add the event to this matrix with fields and deltas.
3) Add or update i18n keys if used and ensure translation resources are registered.
4) Add or update at least one UI test that asserts the details text is payload driven.
