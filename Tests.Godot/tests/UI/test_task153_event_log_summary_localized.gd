extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_TYPE := "core.sanguo.economy.year.price.adjusted"
const RANDOM_EVENT_TYPE := "core.sanguo.random_event.applied"
const CITY_TOLL_PAID_TYPE := "core.sanguo.city.toll.paid"
const CARD_LOST_TYPE := "core.sanguo.card.lost"
const REGION_CAPTURED_TYPE := "core.sanguo.region.captured"
const LOOT_GRANTED_TYPE := "core.sanguo.loot.granted"
const REGION_LOST_TYPE := "core.sanguo.region.lost"
const SEASON_EVENT_TYPE := "core.sanguo.economy.season.event.applied"
const RELIC_APPLIED_TYPE := "core.sanguo.relic.applied"
const CITY_TOLL_SYNERGY_TYPE := "core.sanguo.city.toll.synergy.paid"
const MONTH_SETTLED_TYPE := "core.sanguo.economy.month.settled"
const TOKEN_MOVED_TYPE := "core.sanguo.board.token.moved"
const GAME_ENDED_TYPE := "core.sanguo.game.ended"
const SCORE_UPDATED_TYPE := "core.score.updated"
const AI_DECISION_TYPE := "core.sanguo.ai.decision.made"
const BOSS_CHALLENGE_PROMPTED_TYPE := "core.sanguo.boss.challenge.prompted"
const OBJECTIVE_SKIPPED_TYPE := "core.sanguo.objective.skipped"
const LOCALE_ZH := "zh"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var translated := String(TranslationServer.translate(key))
		if translated.strip_edges().length() > 0 and translated != key:
			return translated
	return ""

func _is_unknown_placeholder(value: String) -> bool:
	var trimmed := value.strip_edges()
	if trimmed.length() == 0:
		return true

	var has_marker := false
	for i in range(trimmed.length()):
		var ch := trimmed[i]
		if ch == "?" or ch == "?" or ch == "?":
			has_marker = true
			continue
		return false

	return has_marker

func _require_translation(key: String) -> String:
	var translated := _try_translate(key)
	assert_bool(translated.strip_edges().length() > 0).is_true()
	return translated

func _normalize_token(token: String) -> String:
	var result := ""
	for i in range(token.length()):
		var ch := token[i]
		if ch == "-" or ch == " ":
			if not result.ends_with("_"):
				result += "_"
		elif ch >= "A" and ch <= "Z":
			if result.length() > 0 and not result.ends_with("_"):
				result += "_"
			result += String(ch).to_lower()
		else:
			result += String(ch).to_lower()
	return result

func _translate_token(category: String, token: String) -> String:
	var normalized := _normalize_token(token)
	var key := "ui.hud.event.shared.detail.%s.%s" % [category, normalized]
	return _require_translation(key)

func _translate_field(event_type: String, section: String, field_key: String, fallback: String) -> String:
	var event_key := "ui.hud.event.%s.%s.%s" % [event_type, section, field_key]
	var translated := _try_translate(event_key)
	if translated.length() > 0:
		return translated
	var shared_key := "ui.hud.event.shared.%s.%s" % [section, field_key]
	translated = _try_translate(shared_key)
	if translated.length() > 0:
		return translated
	return fallback

func _translate_summary(event_type: String) -> String:
	var summary_key := "ui.hud.event.%s.summary" % event_type
	var translated := _try_translate(summary_key)
	if translated.length() > 0:
		return translated
	var title_key := "ui.hud.event.%s.title" % event_type
	translated = _try_translate(title_key)
	if translated.length() > 0:
		return translated
	var shared_key := "ui.hud.event.shared.summary.unknown"
	translated = _try_translate(shared_key)
	if translated.length() > 0:
		return translated
	return "event"

func _publish_year_price_adjusted(data_json: String) -> void:
	_bus.PublishSimple(EVENT_TYPE, "ut", data_json)

func _publish_random_event_applied(data_json: String) -> void:
	_bus.PublishSimple(RANDOM_EVENT_TYPE, "ut", data_json)

func _publish_city_toll_paid(data_json: String) -> void:
	_bus.PublishSimple(CITY_TOLL_PAID_TYPE, "ut", data_json)

func _publish_card_lost(data_json: String) -> void:
	_bus.PublishSimple(CARD_LOST_TYPE, "ut", data_json)

func _publish_region_captured(data_json: String) -> void:
	_bus.PublishSimple(REGION_CAPTURED_TYPE, "ut", data_json)

func _publish_loot_granted(data_json: String) -> void:
	_bus.PublishSimple(LOOT_GRANTED_TYPE, "ut", data_json)

func _publish_region_lost(data_json: String) -> void:
	_bus.PublishSimple(REGION_LOST_TYPE, "ut", data_json)

func _publish_season_event_applied(data_json: String) -> void:
	_bus.PublishSimple(SEASON_EVENT_TYPE, "ut", data_json)

func _publish_relic_applied(data_json: String) -> void:
	_bus.PublishSimple(RELIC_APPLIED_TYPE, "ut", data_json)

func _publish_city_toll_synergy_paid(data_json: String) -> void:
	_bus.PublishSimple(CITY_TOLL_SYNERGY_TYPE, "ut", data_json)

func _publish_month_settled(data_json: String) -> void:
	_bus.PublishSimple(MONTH_SETTLED_TYPE, "ut", data_json)

func _publish_token_moved(data_json: String) -> void:
	_bus.PublishSimple(TOKEN_MOVED_TYPE, "ut", data_json)

func _publish_game_ended(data_json: String) -> void:
	_bus.PublishSimple(GAME_ENDED_TYPE, "ut", data_json)

func _publish_ai_decision_made(data_json: String) -> void:
	_bus.PublishSimple(AI_DECISION_TYPE, "ut", data_json)

func _publish_boss_challenge_prompted(data_json: String) -> void:
	_bus.PublishSimple(BOSS_CHALLENGE_PROMPTED_TYPE, "ut", data_json)

func _publish_objective_skipped(data_json: String) -> void:
	_bus.PublishSimple(OBJECTIVE_SKIPPED_TYPE, "ut", data_json)

func _await_event_log_items(hud: Node, min_count: int = 1, max_frames: int = 10) -> Array:
	var items := _event_log_messages(hud)
	for _i in range(max_frames):
		if items.size() >= min_count:
			return items
		await get_tree().process_frame
		items = _event_log_messages(hud)
	return items

# ACC:T153.1
func test_event_log_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_year_price_adjusted("{\"GameId\":\"g1\",\"TurnNumber\":10,\"Year\":3,\"CityId\":\"tile_01\",\"OldPrice\":100,\"NewPrice\":130,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":0}}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(EVENT_TYPE)
	assert_str(summary).contains(summary_label)

	var city_label := _translate_field(EVENT_TYPE, "detail", "city_id", "city_id")
	var city_name := _require_translation("tile.map001.tile_01.name")
	var year_label := _translate_field(EVENT_TYPE, "detail", "year", "year")
	assert_str(summary).contains(city_label + "=" + city_name)
	assert_str(summary).contains(year_label + "=3")
	assert_str(summary).not_contains(EVENT_TYPE)
	assert_str(summary).not_contains("tile_01")
	assert_str(summary).not_contains("city=")
	assert_str(summary).not_contains("year=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

# ACC:T153.1
func test_task153_fixed_campaign_scenario_summary_is_replay_stable_under_fixed_seed() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var scenario_payload := "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EventId\":\"event_money_small\",\"EffectKind\":\"moneyDelta\",\"TriggerSource\":\"tile\",\"RoundNumber\":7,\"MoneyDelta\":120}"

	var first_hud = await _hud()
	_publish_random_event_applied(scenario_payload)
	await get_tree().process_frame
	var first_items := _event_log_messages(first_hud)
	assert_int(first_items.size()).is_greater_equal(1)
	var first_summary := str(first_items[first_items.size() - 1])

	var summary_label := _translate_summary(RANDOM_EVENT_TYPE)
	assert_str(first_summary).contains(summary_label)

	var source_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source", "trigger_source")
	var source_value := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source.tile", "tile")
	var round_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_round", "trigger_round")
	var impact_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "money_delta", "money_delta")
	assert_str(first_summary).contains(source_label + "=" + source_value)
	assert_str(first_summary).contains(round_label + "=7")
	assert_str(first_summary).contains(impact_label + "=120")

	var second_hud = await _hud()
	_publish_random_event_applied(scenario_payload)
	await get_tree().process_frame
	var second_items := _event_log_messages(second_hud)
	assert_int(second_items.size()).is_greater_equal(1)
	var second_summary := str(second_items[second_items.size() - 1])

	assert_str(second_summary).is_equal(first_summary)

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_random_event_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_random_event_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EventId\":\"event_money_small\",\"EffectKind\":\"moneyDelta\",\"TriggerSource\":\"tile\",\"RoundNumber\":7,\"MoneyDelta\":120}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(RANDOM_EVENT_TYPE)
	assert_str(summary).contains(summary_label)

	var event_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "event_id", "event_id")
	var event_name := _require_translation("event.event_money_small.name")
	assert_str(summary).contains(event_label + "=" + event_name)

	var source_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source", "trigger_source")
	var source_value := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source.tile", "tile")
	var pool_name := _try_translate("event_pool.default.name")
	var expected_source := source_value
	if pool_name.length() > 0 and not _is_unknown_placeholder(pool_name):
		expected_source = pool_name
	assert_str(summary).contains(source_label + "=" + expected_source)

	var round_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_round", "trigger_round")
	assert_str(summary).contains(round_label + "=7")

	assert_str(summary).not_contains(RANDOM_EVENT_TYPE)
	assert_str(summary).not_contains("trigger_source")
	assert_str(summary).not_contains("trigger_round")
	assert_str(summary).not_contains("source=")
	assert_str(summary).not_contains("round=")
	assert_str(summary).not_contains("tile")
	assert_str(summary).not_contains("event_money_small")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_city_toll_paid_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_city_toll_paid("{\"GameId\":\"g1\",\"TurnNumber\":10,\"PayerId\":\"p1\",\"OwnerId\":\"p2\",\"CityId\":\"tile_01\",\"Amount\":200,\"OwnerAmount\":150}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CITY_TOLL_PAID_TYPE)
	assert_str(summary).contains(summary_label)

	var payer_label := _translate_field(CITY_TOLL_PAID_TYPE, "detail", "payer_id", "payer")
	var amount_label := _translate_field(CITY_TOLL_PAID_TYPE, "detail", "amount", "amount")
	var city_label := _translate_field(CITY_TOLL_PAID_TYPE, "detail", "city_id", "city_id")
	var city_name := _require_translation("tile.map001.tile_01.name")
	assert_str(summary).contains(payer_label + "=p1")
	assert_str(summary).contains(amount_label + "=200")
	assert_str(summary).contains(city_label + "=" + city_name)

	assert_str(summary).not_contains(CITY_TOLL_PAID_TYPE)
	assert_str(summary).not_contains("tile_01")
	assert_str(summary).not_contains("payer=")
	assert_str(summary).not_contains("amount=")
	assert_str(summary).not_contains("city=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_card_lost_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_card_lost("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"CardId\":\"card_coupon\",\"ReasonCode\":\"consumed\",\"SourceKind\":\"action_card\",\"SourceId\":\"card_coupon\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CARD_LOST_TYPE)
	assert_str(summary).contains(summary_label)

	var card_label := _translate_field(CARD_LOST_TYPE, "detail", "card_id", "card_id")
	var reason_label := _translate_field(CARD_LOST_TYPE, "detail", "reason_code", "reason_code")
	var reason_value := _translate_field(CARD_LOST_TYPE, "detail", "reason_code.consumed", "consumed")
	var card_name := _require_translation("card.card_coupon.name")
	assert_str(summary).contains(card_label + "=" + card_name)
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(CARD_LOST_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("consumed")
	assert_str(summary).not_contains("card_coupon")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_region_captured_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_region_captured("{\"GameId\":\"g1\",\"RegionId\":\"region_01\",\"OwnerId\":\"p2\",\"ReasonCode\":\"captured\",\"CityIds\":[\"tile_01\",\"tile_02\",\"tile_03\"]}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(REGION_CAPTURED_TYPE)
	assert_str(summary).contains(summary_label)

	var region_label := _translate_field(REGION_CAPTURED_TYPE, "detail", "region_id", "region_id")
	var owner_label := _translate_field(REGION_CAPTURED_TYPE, "detail", "owner_id", "owner_id")
	var reason_label := _translate_field(REGION_CAPTURED_TYPE, "detail", "reason_code", "reason_code")
	var reason_value := _translate_field(REGION_CAPTURED_TYPE, "detail", "reason_code.captured", "captured")
	var region_name := _require_translation("region.region_01.name")
	assert_str(summary).contains(region_label + "=" + region_name)
	assert_str(summary).contains(owner_label + "=p2")
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(REGION_CAPTURED_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("captured")
	assert_str(summary).not_contains("region_01")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_loot_granted_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_loot_granted("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"LootKind\":\"card\",\"CardId\":\"card_coupon\",\"MoneyDelta\":100,\"SourceKind\":\"event\",\"SourceId\":\"event_money_small\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(LOOT_GRANTED_TYPE)
	assert_str(summary).contains(summary_label)

	var loot_label := _translate_field(LOOT_GRANTED_TYPE, "detail", "loot_kind", "loot_kind")
	var card_label := _translate_field(LOOT_GRANTED_TYPE, "detail", "card_id", "card_id")
	var loot_kind_value := _translate_token("loot_kind", "card")
	var card_name := _require_translation("card.card_coupon.name")
	assert_str(summary).contains(loot_label + "=" + loot_kind_value)
	assert_str(summary).contains(card_label + "=" + card_name)

	assert_str(summary).not_contains(LOOT_GRANTED_TYPE)
	assert_str(summary).not_contains("loot_kind")
	assert_str(summary).not_contains("card_id")
	assert_str(summary).not_contains("card_coupon")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_region_lost_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_region_lost("{\"GameId\":\"g1\",\"RegionId\":\"region_02\",\"OwnerId\":\"p2\",\"ReasonCode\":\"lost_last_city\",\"TriggerCityId\":\"tile_01\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(REGION_LOST_TYPE)
	assert_str(summary).contains(summary_label)

	var region_label := _translate_field(REGION_LOST_TYPE, "detail", "region_id", "region_id")
	var reason_label := _translate_field(REGION_LOST_TYPE, "detail", "reason_code", "reason_code")
	var reason_value := _translate_field(REGION_LOST_TYPE, "detail", "reason_code.lost_last_city", "lost_last_city")
	var region_name := _require_translation("region.region_02.name")
	assert_str(summary).contains(region_label + "=" + region_name)
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(REGION_LOST_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("lost_last_city")
	assert_str(summary).not_contains("region_02")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_season_event_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_season_event_applied("{\"GameId\":\"g1\",\"TurnNumber\":12,\"Year\":2,\"Season\":3,\"YieldMultiplier\":1.2}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(SEASON_EVENT_TYPE)
	assert_str(summary).contains(summary_label)

	var year_label := _translate_field(SEASON_EVENT_TYPE, "detail", "year", "year")
	var season_label := _translate_field(SEASON_EVENT_TYPE, "detail", "season", "season")
	assert_str(summary).contains(year_label + "=2")
	assert_str(summary).contains(season_label + "=3")

	assert_str(summary).not_contains(SEASON_EVENT_TYPE)
	assert_str(summary).not_contains("year=")
	assert_str(summary).not_contains("season=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_relic_applied_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_relic_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"RelicId\":\"relic_gold_pouch\",\"EffectKind\":\"moneyDelta\",\"MoneyDelta\":50}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(RELIC_APPLIED_TYPE)
	assert_str(summary).contains(summary_label)

	var relic_label := _translate_field(RELIC_APPLIED_TYPE, "detail", "relic_id", "relic_id")
	var kind_label := _translate_field(RELIC_APPLIED_TYPE, "detail", "effect_kind", "effect_kind")
	var relic_name := _require_translation("relic.relic_gold_pouch.name")
	var effect_value := _translate_token("effect_kind", "moneyDelta")
	assert_str(summary).contains(relic_label + "=" + relic_name)
	assert_str(summary).contains(kind_label + "=" + effect_value)

	assert_str(summary).not_contains(RELIC_APPLIED_TYPE)
	assert_str(summary).not_contains("relic_id")
	assert_str(summary).not_contains("effect_kind")
	assert_str(summary).not_contains("relic_gold_pouch")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_city_toll_synergy_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_city_toll_synergy_paid("{\"GameId\":\"g1\",\"TurnNumber\":10,\"PayerId\":\"p1\",\"OwnerId\":\"p2\",\"LandingCityId\":\"tile_01\",\"RegionId\":\"region_02\",\"PaidTotalAmount\":500,\"PaidCitiesCount\":3}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CITY_TOLL_SYNERGY_TYPE)
	assert_str(summary).contains(summary_label)

	var payer_label := _translate_field(CITY_TOLL_SYNERGY_TYPE, "detail", "payer_id", "payer_id")
	var region_label := _translate_field(CITY_TOLL_SYNERGY_TYPE, "detail", "region_id", "region_id")
	var region_name := _require_translation("region.region_02.name")
	assert_str(summary).contains(payer_label + "=p1")
	assert_str(summary).contains(region_label + "=" + region_name)

	assert_str(summary).not_contains(CITY_TOLL_SYNERGY_TYPE)
	assert_str(summary).not_contains("payer_id")
	assert_str(summary).not_contains("region_id")
	assert_str(summary).not_contains("region_02")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_month_settled_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_month_settled("{\"GameId\":\"g1\",\"TurnNumber\":12,\"Year\":2,\"Month\":5}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(MONTH_SETTLED_TYPE)
	assert_str(summary).contains(summary_label)

	var year_label := _translate_field(MONTH_SETTLED_TYPE, "detail", "year", "year")
	var month_label := _translate_field(MONTH_SETTLED_TYPE, "detail", "month", "month")
	assert_str(summary).contains(year_label + "=2")
	assert_str(summary).contains(month_label + "=5")

	assert_str(summary).not_contains(MONTH_SETTLED_TYPE)
	assert_str(summary).not_contains("year=")
	assert_str(summary).not_contains("month=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_token_moved_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_token_moved("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"FromIndex\":2,\"ToIndex\":6,\"Steps\":4,\"PassedStart\":true}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(TOKEN_MOVED_TYPE)
	assert_str(summary).contains(summary_label)

	var from_label := _translate_field(TOKEN_MOVED_TYPE, "detail", "from_index", "from_index")
	var to_label := _translate_field(TOKEN_MOVED_TYPE, "detail", "to_index", "to_index")
	assert_str(summary).contains(from_label + "=2")
	assert_str(summary).contains(to_label + "=6")

	assert_str(summary).not_contains(TOKEN_MOVED_TYPE)
	assert_str(summary).not_contains("from_index")
	assert_str(summary).not_contains("to_index")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_game_ended_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_game_ended("{\"GameId\":\"g1\",\"EndReason\":\"player_bankrupt\",\"WinnerPlayerId\":\"p2\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(GAME_ENDED_TYPE)
	assert_str(summary).contains(summary_label)

	var reason_label := _translate_field(GAME_ENDED_TYPE, "detail", "end_reason", "end_reason")
	var winner_label := _translate_field(GAME_ENDED_TYPE, "detail", "winner_player_id", "winner_player_id")
	var reason_value := _translate_token("end_reason", "player_bankrupt")
	assert_str(summary).contains(reason_label + "=" + reason_value)
	assert_str(summary).contains(winner_label + "=p2")

	assert_str(summary).not_contains(GAME_ENDED_TYPE)
	assert_str(summary).not_contains("end_reason")
	assert_str(summary).not_contains("winner_player_id")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_ai_decision_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_ai_decision_made("{\"GameId\":\"g1\",\"AiPlayerId\":\"ai-1\",\"DecisionType\":\"RollDice\",\"DecisionNode\":\"sanguo.ai.decision.roll_unless_blocked.v1\",\"FromState\":\"RollDice\",\"ToState\":\"RollDice\",\"Reason\":\"rules_allow_roll\",\"OccurredAt\":\"2025-01-01T00:00:00Z\",\"CorrelationId\":\"c1\"}")
	for _i in range(10):
		await get_tree().process_frame
		var pending := _event_log_messages(hud)
		if pending.size() > 0:
			break

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(AI_DECISION_TYPE)
	assert_str(summary).contains(summary_label)

	var player_label := _translate_field(AI_DECISION_TYPE, "detail", "ai_player_id", "ai_player_id")
	var decision_label := _translate_field(AI_DECISION_TYPE, "detail", "decision_type", "decision_type")
	var reason_label := _translate_field(AI_DECISION_TYPE, "detail", "reason", "reason")
	var decision_value := _translate_token("decision_type", "RollDice")
	var reason_value := _translate_field(AI_DECISION_TYPE, "detail", "reason_code.rules_allow_roll", "rules_allow_roll")

	assert_str(summary).contains(player_label + "=ai-1")
	assert_str(summary).contains(decision_label + "=" + decision_value)
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(AI_DECISION_TYPE)
	assert_str(summary).not_contains("RollDice")
	assert_str(summary).not_contains("rules_allow_roll")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_fallback_value_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_bus.PublishSimple(SCORE_UPDATED_TYPE, "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":5}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])

	var summary_label := _translate_summary(SCORE_UPDATED_TYPE)
	assert_str(summary).contains(summary_label)

	var player_label := _translate_field(SCORE_UPDATED_TYPE, "detail", "player_id", "player_id")
	var value_label := _translate_field(SCORE_UPDATED_TYPE, "detail", "value", "value")
	assert_str(summary).contains(player_label + "=p1")
	assert_str(summary).contains(value_label + "=5")

	assert_str(summary).not_contains(SCORE_UPDATED_TYPE)
	assert_str(summary).not_contains("player=")
	assert_str(summary).not_contains("value=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_boss_challenge_prompted_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_boss_challenge_prompted("{\"GameId\":\"g1\",\"BossId\":\"boss_1\",\"RoundNumber\":6,\"WinRateTier\":\"mid\",\"NextRoundPressureForecast\":4,\"KeyLossSummary\":\"camp_hp_risk\",\"FailConsequence\":\"return_to_camp_end_round\"}")
	var items := await _await_event_log_items(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(BOSS_CHALLENGE_PROMPTED_TYPE)
	assert_str(summary).contains(summary_label)

	var win_rate_label := _translate_field(BOSS_CHALLENGE_PROMPTED_TYPE, "detail", "win_rate_tier", "win_rate_tier")
	var win_rate_value := _translate_token("win_rate_tier", "mid")
	var fail_label := _translate_field(BOSS_CHALLENGE_PROMPTED_TYPE, "detail", "fail_consequence", "fail_consequence")
	var fail_value := _translate_token("fail_consequence", "return_to_camp_end_round")
	var loss_label := _translate_field(BOSS_CHALLENGE_PROMPTED_TYPE, "detail", "key_loss_summary", "key_loss_summary")
	var loss_value := _translate_token("key_loss_summary", "camp_hp_risk")
	var round_label := _translate_field(BOSS_CHALLENGE_PROMPTED_TYPE, "detail", "trigger_round", "trigger_round")

	assert_str(summary).contains(win_rate_label + "=" + win_rate_value)
	assert_str(summary).contains(fail_label + "=" + fail_value)
	assert_str(summary).contains(loss_label + "=" + loss_value)
	assert_str(summary).contains(round_label + "=6")

	assert_str(summary).not_contains(BOSS_CHALLENGE_PROMPTED_TYPE)
	assert_str(summary).not_contains("win_rate_tier")
	assert_str(summary).not_contains("mid")
	assert_str(summary).not_contains("return_to_camp_end_round")
	assert_str(summary).not_contains("camp_hp_risk")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_objective_skipped_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_objective_skipped("{\"GameId\":\"g1\",\"ObjectiveId\":\"obj_01\",\"RoundNumber\":6,\"Reason\":\"run_ended_in_boss\",\"BossId\":\"boss_1\"}")
	var items := await _await_event_log_items(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(OBJECTIVE_SKIPPED_TYPE)
	assert_str(summary).contains(summary_label)

	var reason_label := _translate_field(OBJECTIVE_SKIPPED_TYPE, "detail", "reason", "reason")
	var reason_value := _translate_token("objective_skip_reason", "run_ended_in_boss")
	var round_label := _translate_field(OBJECTIVE_SKIPPED_TYPE, "detail", "trigger_round", "trigger_round")
	assert_str(summary).contains(reason_label + "=" + reason_value)
	assert_str(summary).contains(round_label + "=6")

	assert_str(summary).not_contains(OBJECTIVE_SKIPPED_TYPE)
	assert_str(summary).not_contains("run_ended_in_boss")
	assert_str(summary).not_contains("reason=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)
