extends "res://tests/UI/_fixtures/ui_event_log_fixture.gd"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var t := String(TranslationServer.translate(key))
		if t.strip_edges().length() > 0 and t != key:
			return t
	return ""

func _translate_field(event_type: String, section: String, field_key: String, fallback: String) -> String:
	var event_key := "ui.hud.event.%s.%s.%s" % [event_type, section, field_key]
	var text := _try_translate(event_key)
	if text.length() > 0:
		return text
	var shared_key := "ui.hud.event.shared.%s.%s" % [section, field_key]
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return fallback

func _translate_reason(event_type: String, reason: String) -> String:
	var specific_key := "ui.hud.event.%s.detail.reason_code.%s" % [event_type, reason]
	var text := _try_translate(specific_key)
	if text.length() > 0:
		return text
	var shared_key := "ui.hud.event.shared.detail.reason_code.%s" % reason
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return reason

func _translate_token(event_type: String, category: String, token: String) -> String:
	var normalized := token.strip_edges().to_lower()
	var specific_key := "ui.hud.event.%s.detail.%s.%s" % [event_type, category, normalized]
	var text := _try_translate(specific_key)
	if text.length() > 0:
		return text
	var shared_key := "ui.hud.event.shared.detail.%s.%s" % [category, normalized]
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return token

func _await_details(log_list: ItemList, details: Label) -> void:
	for _i in range(12):
		await get_tree().process_frame
		if log_list.get_item_count() > 0 and str(details.text).length() > 0:
			return

func _assert_detail_contains(detail_text: String, event_type: String, section: String, field_key: String, expected_value: String) -> void:
	var label := _translate_field(event_type, section, field_key, field_key)
	assert_str(detail_text).contains(label + ": " + expected_value)

func test_event_log_details_show_additional_event_facts() -> void:
	var original_locale := _set_locale("zh")
	var hud = await _hud()
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	var details: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")

	var card_name := _try_translate("card.card_coupon.name")
	var map_name := _try_translate("map.map001.name")
	var reason_bought := _translate_reason("core.sanguo.city.owner.changed", "bought")
	var reason_bankrupt := _translate_reason("core.sanguo.player.eliminated", "bankrupt")
	var combat_outcome := _translate_token("core.sanguo.combat.ended", "outcome", "win")

	var cases: Array = [
		{
			"type": "core.sanguo.action_card.played",
			"json": "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"CardId\":\"card_coupon\",\"EffectKind\":\"economy_step_delta\",\"StepDelta\":2,\"DurationRounds\":2,\"AppliedMultipliersAfter\":{\"BaseSteps\":1,\"EffectiveSteps\":2}}",
			"expected": [
				{"section": "detail", "key": "card_id", "value": card_name},
				{"section": "detail", "key": "duration_rounds", "value": "2"},
				{"section": "delta", "key": "step_delta", "value": "+2"},
			],
		},
		{
			"type": "core.sanguo.city.owner.changed",
			"json": "{\"GameId\":\"g1\",\"TurnNumber\":4,\"CityId\":\"tile_01\",\"OldOwnerId\":\"p1\",\"NewOwnerId\":\"p2\",\"ReasonCode\":\"bought\"}",
			"expected": [
				{"section": "detail", "key": "city_id", "value": _try_translate("tile.map001.tile_01.name")},
				{"section": "detail", "key": "reason_code", "value": reason_bought},
			],
		},
		{
			"type": "core.sanguo.combat.started",
			"json": "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EncounterId\":\"enc_01\",\"RandomSeed\":7}",
			"expected": [
				{"section": "detail", "key": "encounter_id", "value": "enc_01"},
				{"section": "detail", "key": "random_seed", "value": "7"},
			],
		},
		{
			"type": "core.sanguo.combat.ended",
			"json": "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EncounterId\":\"enc_01\",\"Result\":{\"Outcome\":\"win\",\"MoneyDelta\":20,\"EncounterTarget\":5,\"EffectiveCombatRating\":7}}",
			"expected": [
				{"section": "detail", "key": "outcome", "value": combat_outcome},
				{"section": "detail", "key": "encounter_target", "value": "5"},
				{"section": "delta", "key": "money_delta", "value": "+20"},
			],
		},
		{
			"type": "core.sanguo.game.started",
			"json": "{\"GameId\":\"g1\",\"MapId\":\"map001\",\"PlayersCount\":2,\"StartingMoneyPreset\":1000,\"GlobalEventIntervalTurns\":3,\"RandomSeed\":7}",
			"expected": [
				{"section": "detail", "key": "map_id", "value": map_name},
				{"section": "detail", "key": "players_count", "value": "2"},
			],
		},
		{
			"type": "core.sanguo.game.turn.started",
			"json": "{\"GameId\":\"g1\",\"TurnNumber\":1,\"ActivePlayerId\":\"p1\",\"Year\":1,\"Month\":2,\"Day\":3}",
			"expected": [
				{"section": "detail", "key": "year", "value": "1"},
				{"section": "detail", "key": "active_player_id", "value": "p1"},
			],
		},
		{
			"type": "core.sanguo.game.turn.advanced",
			"json": "{\"GameId\":\"g1\",\"TurnNumber\":2,\"ActivePlayerId\":\"p2\",\"Year\":1,\"Month\":3,\"Day\":1}",
			"expected": [
				{"section": "detail", "key": "month", "value": "3"},
				{"section": "detail", "key": "active_player_id", "value": "p2"},
			],
		},
		{
			"type": "core.sanguo.game.turn.ended",
			"json": "{\"GameId\":\"g1\",\"TurnNumber\":2,\"ActivePlayerId\":\"p2\",\"Year\":1,\"Month\":3,\"Day\":1}",
			"expected": [
				{"section": "detail", "key": "day", "value": "1"},
				{"section": "detail", "key": "active_player_id", "value": "p2"},
			],
		},
		{
			"type": "core.sanguo.game.saved",
			"json": "{\"GameId\":\"g1\",\"SaveSlotId\":\"slot_1\"}",
			"expected": [
				{"section": "detail", "key": "save_slot_id", "value": "slot_1"},
			],
		},
		{
			"type": "core.sanguo.game.loaded",
			"json": "{\"GameId\":\"g1\",\"SaveSlotId\":\"slot_2\"}",
			"expected": [
				{"section": "detail", "key": "save_slot_id", "value": "slot_2"},
			],
		},
		{
			"type": "core.sanguo.player.eliminated",
			"json": "{\"GameId\":\"g1\",\"TurnNumber\":5,\"PlayerId\":\"p1\",\"ReasonCode\":\"bankrupt\",\"MoneyBefore\":10,\"MoneyAfter\":0}",
			"expected": [
				{"section": "detail", "key": "reason_code", "value": reason_bankrupt},
				{"section": "detail", "key": "money_before", "value": "10"},
				{"section": "detail", "key": "money_after", "value": "0"},
			],
		},
	]

	for item in cases:
		log_list.clear()
		details.text = ""

		_bus.PublishSimple(String(item["type"]), "ut", String(item["json"]))
		await _await_details(log_list, details)

		assert_int(log_list.get_item_count()).is_equal(1)
		var detail_text := str(details.text)
		for expected in item["expected"]:
			_assert_detail_contains(detail_text, String(item["type"]), String(expected["section"]), String(expected["key"]), String(expected["value"]))

	_restore_locale(original_locale)
