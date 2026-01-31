extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

var _last_data_json := ""

func before_test() -> void:
	await _setup_event_bus()
	_connect_domain_event_emitted(Callable(self, "_on_domain_event_emitted"))
	_last_data_json = ""

func after_test() -> void:
	await _teardown_event_bus()

func _on_domain_event_emitted(_type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	_last_data_json = str(data_json)

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for i in range(list.item_count):
		items.append(str(list.get_item_text(i)))
	return items

func _event_log_details(hud: Node) -> String:
	var panel: Control = hud.get_node("EventLogPanel")
	var details: Label = panel.get_node("Margin/VBox/Details/Scroll/DetailsText")
	return str(details.text)

func _publish_city_bought(data_json: String) -> void:
	_bus.PublishSimple("core.sanguo.city.bought", "ut", data_json)

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

# acceptance: ACC:T51.3
func test_task51_event_log_shows_effective_multiplier_but_hides_breakdown_when_sources_none() -> void:
	var hud = await _hud()

	_publish_city_bought("{\"CityId\":\"tile_01\",\"Price\":50,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":0}}")
	await get_tree().process_frame

	assert_str(_last_data_json).contains("AppliedMultipliers")

	var msgs := _event_log_messages(hud)
	assert_int(msgs.size()).is_greater_equal(1)
	var last := str(msgs[msgs.size() - 1])
	var multiplier_label := _translate_field("core.sanguo.city.bought", "detail", "mult.effective_multiplier", "effective_multiplier")
	assert_str(last).contains(multiplier_label + "=1.5")
	assert_str(last).not_contains("core.sanguo.city.bought")
	assert_str(last).not_contains(" c=")
	assert_str(last).not_contains(" b=")
	assert_str(last).not_contains(" e=")
	assert_str(last).not_contains(" a=")

# acceptance: ACC:T51.4
func test_task51_event_log_can_show_breakdown_when_sources_provided() -> void:
	var hud = await _hud()

	_publish_city_bought("{\"CityId\":\"tile_01\",\"Price\":50,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":1,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":1}}")
	await get_tree().process_frame

	assert_str(_last_data_json).contains("AppliedMultipliers")

	var msgs := _event_log_messages(hud)
	assert_int(msgs.size()).is_greater_equal(1)
	var last := str(msgs[msgs.size() - 1])
	var multiplier_label := _translate_field("core.sanguo.city.bought", "detail", "mult.effective_multiplier", "effective_multiplier")
	assert_str(last).contains(multiplier_label + "=1.5")

	var details := _event_log_details(hud)
	var additive_label := _translate_field("core.sanguo.city.bought", "detail", "mult.additive", "additive")
	var multiplicative_label := _translate_field("core.sanguo.city.bought", "detail", "mult.multiplicative", "multiplicative")
	var base_steps_label := _translate_field("core.sanguo.city.bought", "detail", "mult.base_steps", "base_steps")
	var character_delta_label := _translate_field("core.sanguo.city.bought", "detail", "mult.character_step_delta", "character_step_delta")
	var effective_steps_label := _translate_field("core.sanguo.city.bought", "detail", "mult.effective_steps", "effective_steps")
	var effective_multiplier_label := _translate_field("core.sanguo.city.bought", "detail", "mult.effective_multiplier", "effective_multiplier")

	assert_str(details).contains(additive_label + ":")
	assert_str(details).contains(base_steps_label + ": 2")
	assert_str(details).contains(character_delta_label + ": +1")

	assert_str(details).contains(multiplicative_label + ":")
	assert_str(details).contains(effective_steps_label + ": 3")
	assert_str(details).contains(effective_multiplier_label + ": 1.5")

