extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const RANDOM_EVENT_TYPE := "core.sanguo.random_event.applied"
const LOCALE_EN := "en"

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

func _publish_random_event_applied(data_json: String) -> void:
	_bus.PublishSimple(RANDOM_EVENT_TYPE, "ut", data_json)

func test_newbie_loop_event_log_orders_tile_before_global() -> void:
	var original_locale := _set_locale(LOCALE_EN)
	var hud := await _hud()
	var baseline := _event_log_messages(hud).size()

	_publish_random_event_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EventId\":\"event_money_small\",\"EffectKind\":\"moneyDelta\",\"TriggerSource\":\"tile\",\"RoundNumber\":1,\"MoneyDelta\":10}")
	_publish_random_event_applied("{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EventId\":\"event_economy_boost\",\"EffectKind\":\"moneyDelta\",\"TriggerSource\":\"global\",\"RoundNumber\":1,\"MoneyDelta\":20}")

	var items: Array = []
	for _i in range(60):
		items = _event_log_messages(hud)
		if items.size() >= baseline + 2:
			break
		await get_tree().process_frame

	assert_int(items.size()).is_greater_equal(baseline + 2)

	var source_label := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source", "source")
	var source_tile := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source.tile", "tile")
	var source_global := _translate_field(RANDOM_EVENT_TYPE, "detail", "trigger_source.global", "global")

	var tile_summary := str(items[baseline])
	var global_summary := str(items[baseline + 1])

	assert_str(tile_summary).contains(source_label + "=" + source_tile)
	assert_str(global_summary).contains(source_label + "=" + source_global)

	_restore_locale(original_locale)
