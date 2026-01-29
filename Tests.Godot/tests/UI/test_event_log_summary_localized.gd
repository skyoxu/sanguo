extends "res://tests/UI/_fixtures/ui_event_log_fixture.gd"

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

func test_event_log_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_year_price_adjusted("{\"GameId\":\"g1\",\"TurnNumber\":10,\"Year\":3,\"CityId\":\"c9\",\"OldPrice\":100,\"NewPrice\":130,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":0}}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(EVENT_TYPE)
	assert_str(summary).contains(summary_label)

	var city_label := _translate_field(EVENT_TYPE, "detail", "city_id", "city_id")
	var year_label := _translate_field(EVENT_TYPE, "detail", "year", "year")
	assert_str(summary).contains(city_label + "=c9")
	assert_str(summary).contains(year_label + "=3")
	assert_str(summary).not_contains(EVENT_TYPE)
	assert_str(summary).not_contains("city=")
	assert_str(summary).not_contains("year=")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_random_event_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_random_event_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EventId\":\"re_01\",\"EffectKind\":\"money\",\"TriggerSource\":\"tile\",\"RoundNumber\":7,\"MoneyDelta\":120}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(RANDOM_EVENT_TYPE)
	assert_str(summary).contains(summary_label)

	var source_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source", "trigger_source")
	var source_value := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source.tile", "tile")
	assert_str(summary).contains(source_label + "=" + source_value)

	var round_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_round", "trigger_round")
	assert_str(summary).contains(round_label + "=7")

	assert_str(summary).not_contains(RANDOM_EVENT_TYPE)
	assert_str(summary).not_contains("trigger_source")
	assert_str(summary).not_contains("trigger_round")
	assert_str(summary).not_contains("source=")
	assert_str(summary).not_contains("round=")
	assert_str(summary).not_contains("tile")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_city_toll_paid_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_city_toll_paid("{\"GameId\":\"g1\",\"TurnNumber\":10,\"PayerId\":\"p1\",\"OwnerId\":\"p2\",\"CityId\":\"c1\",\"Amount\":200,\"OwnerAmount\":150}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CITY_TOLL_PAID_TYPE)
	assert_str(summary).contains(summary_label)

	var payer_label := _translate_field(CITY_TOLL_PAID_TYPE, "detail", "payer_id", "payer")
	var amount_label := _translate_field(CITY_TOLL_PAID_TYPE, "detail", "amount", "amount")
	assert_str(summary).contains(payer_label + "=p1")
	assert_str(summary).contains(amount_label + "=200")

	assert_str(summary).not_contains(CITY_TOLL_PAID_TYPE)
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
	_publish_card_lost("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"CardId\":\"card_1\",\"ReasonCode\":\"consumed\",\"SourceKind\":\"action_card\",\"SourceId\":\"ac_01\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CARD_LOST_TYPE)
	assert_str(summary).contains(summary_label)

	var card_label := _translate_field(CARD_LOST_TYPE, "detail", "card_id", "card_id")
	var reason_label := _translate_field(CARD_LOST_TYPE, "detail", "reason_code", "reason_code")
	var reason_value := _translate_field(CARD_LOST_TYPE, "detail", "reason_code.consumed", "consumed")
	assert_str(summary).contains(card_label + "=card_1")
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(CARD_LOST_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("consumed")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_region_captured_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_region_captured("{\"GameId\":\"g1\",\"RegionId\":\"r1\",\"OwnerId\":\"p2\",\"ReasonCode\":\"captured\",\"CityIds\":[\"c1\",\"c2\",\"c3\"]}")
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
	assert_str(summary).contains(region_label + "=r1")
	assert_str(summary).contains(owner_label + "=p2")
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(REGION_CAPTURED_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("captured")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_loot_granted_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_loot_granted("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"LootKind\":\"card\",\"CardId\":\"card_1\",\"RelicId\":\"relic_1\",\"MoneyDelta\":100,\"SourceKind\":\"tile\",\"SourceId\":\"t10\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(LOOT_GRANTED_TYPE)
	assert_str(summary).contains(summary_label)

	var loot_label := _translate_field(LOOT_GRANTED_TYPE, "detail", "loot_kind", "loot_kind")
	var card_label := _translate_field(LOOT_GRANTED_TYPE, "detail", "card_id", "card_id")
	assert_str(summary).contains(loot_label + "=card")
	assert_str(summary).contains(card_label + "=card_1")

	assert_str(summary).not_contains(LOOT_GRANTED_TYPE)
	assert_str(summary).not_contains("loot_kind")
	assert_str(summary).not_contains("card_id")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_region_lost_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_region_lost("{\"GameId\":\"g1\",\"RegionId\":\"r1\",\"OwnerId\":\"p2\",\"ReasonCode\":\"lost_last_city\",\"TriggerCityId\":\"c9\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(REGION_LOST_TYPE)
	assert_str(summary).contains(summary_label)

	var region_label := _translate_field(REGION_LOST_TYPE, "detail", "region_id", "region_id")
	var reason_label := _translate_field(REGION_LOST_TYPE, "detail", "reason_code", "reason_code")
	var reason_value := _translate_field(REGION_LOST_TYPE, "detail", "reason_code.lost_last_city", "lost_last_city")
	assert_str(summary).contains(region_label + "=r1")
	assert_str(summary).contains(reason_label + "=" + reason_value)

	assert_str(summary).not_contains(REGION_LOST_TYPE)
	assert_str(summary).not_contains("reason_code")
	assert_str(summary).not_contains("lost_last_city")

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
	_publish_relic_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"RelicId\":\"relic_1\",\"EffectKind\":\"money\",\"MoneyDelta\":50}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(RELIC_APPLIED_TYPE)
	assert_str(summary).contains(summary_label)

	var relic_label := _translate_field(RELIC_APPLIED_TYPE, "detail", "relic_id", "relic_id")
	var kind_label := _translate_field(RELIC_APPLIED_TYPE, "detail", "effect_kind", "effect_kind")
	assert_str(summary).contains(relic_label + "=relic_1")
	assert_str(summary).contains(kind_label + "=money")

	assert_str(summary).not_contains(RELIC_APPLIED_TYPE)
	assert_str(summary).not_contains("relic_id")
	assert_str(summary).not_contains("effect_kind")

	if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
		TranslationServer.set_locale(original_locale)

func test_city_toll_synergy_summary_is_localized_and_avoids_raw_tokens() -> void:
	var original_locale := ""
	if TranslationServer.has_method("get_locale"):
		original_locale = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(LOCALE_ZH)

	var hud = await _hud()
	_publish_city_toll_synergy_paid("{\"GameId\":\"g1\",\"TurnNumber\":10,\"PayerId\":\"p1\",\"OwnerId\":\"p2\",\"LandingCityId\":\"c1\",\"RegionId\":\"r2\",\"PaidTotalAmount\":500,\"PaidCitiesCount\":3}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(CITY_TOLL_SYNERGY_TYPE)
	assert_str(summary).contains(summary_label)

	var payer_label := _translate_field(CITY_TOLL_SYNERGY_TYPE, "detail", "payer_id", "payer_id")
	var region_label := _translate_field(CITY_TOLL_SYNERGY_TYPE, "detail", "region_id", "region_id")
	assert_str(summary).contains(payer_label + "=p1")
	assert_str(summary).contains(region_label + "=r2")

	assert_str(summary).not_contains(CITY_TOLL_SYNERGY_TYPE)
	assert_str(summary).not_contains("payer_id")
	assert_str(summary).not_contains("region_id")

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
	_publish_game_ended("{\"GameId\":\"g1\",\"EndReason\":\"bankrupt\",\"WinnerPlayerId\":\"p2\"}")
	await get_tree().process_frame

	var items := _event_log_messages(hud)
	assert_int(items.size()).is_greater_equal(1)
	var summary := str(items[items.size() - 1])
	var summary_label := _translate_summary(GAME_ENDED_TYPE)
	assert_str(summary).contains(summary_label)

	var reason_label := _translate_field(GAME_ENDED_TYPE, "detail", "end_reason", "end_reason")
	var winner_label := _translate_field(GAME_ENDED_TYPE, "detail", "winner_player_id", "winner_player_id")
	assert_str(summary).contains(reason_label + "=bankrupt")
	assert_str(summary).contains(winner_label + "=p2")

	assert_str(summary).not_contains(GAME_ENDED_TYPE)
	assert_str(summary).not_contains("end_reason")
	assert_str(summary).not_contains("winner_player_id")

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
