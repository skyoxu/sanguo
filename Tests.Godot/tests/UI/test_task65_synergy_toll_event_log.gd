extends "res://tests/UI/_fixtures/ui_event_log_fixture.gd"

const EVENT_TYPE_SYNERGY_TOLL = "core.sanguo.city.toll.synergy.paid"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

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

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var t = String(TranslationServer.translate(key))
		if t.strip_edges().length() > 0 and t != key:
			return t
	return ""

func _translate_field(event_type: String, section: String, field_key: String, fallback: String) -> String:
	var event_key = "ui.hud.event.%s.%s.%s" % [event_type, section, field_key]
	var text = _try_translate(event_key)
	if text.length() > 0:
		return text
	var shared_key = "ui.hud.event.shared.%s.%s" % [section, field_key]
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return fallback

func _translate_summary(event_type: String) -> String:
	var summary_key = "ui.hud.event.%s.summary" % event_type
	var text = _try_translate(summary_key)
	if text.length() > 0:
		return text
	var title_key = "ui.hud.event.%s.title" % event_type
	text = _try_translate(title_key)
	if text.length() > 0:
		return text
	var shared_key = "ui.hud.event.shared.summary.unknown"
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return "event"

func _publish_synergy_toll(data_json: String) -> void:
	_bus.PublishSimple(EVENT_TYPE_SYNERGY_TOLL, "ut", data_json)


# ACC:T65.6
# Synergy toll summary event must be visible in the HUD log with breakdown and multiplier snapshots.
func test_task65_event_log_shows_synergy_toll_breakdown_and_multipliers() -> void:
	var hud = await _hud()

	_publish_synergy_toll("{\"GameId\":\"g1\",\"TurnNumber\":12,\"PayerId\":\"p1\",\"OwnerId\":\"o1\",\"LandingCityId\":\"c1\",\"RegionId\":\"r1\",\"ExpectedTotalAmount\":8,\"PaidTotalAmount\":8,\"ExpectedCitiesCount\":2,\"PaidCitiesCount\":2,\"Breakdown\":[{\"CityId\":\"c1\",\"Amount\":3,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":1,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":2}},{\"CityId\":\"c2\",\"Amount\":5,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":1,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":2}}]}")
	await get_tree().process_frame

	var msgs = _event_log_messages(hud)
	assert_int(msgs.size()).is_greater_equal(1)
	var last = str(msgs[msgs.size() - 1])
	var summary_label = _translate_summary(EVENT_TYPE_SYNERGY_TOLL)
	assert_str(last).contains(summary_label)
	assert_str(last).not_contains(EVENT_TYPE_SYNERGY_TOLL)

	var details = _event_log_details(hud)
	var landing_city_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "landing_city_id", "landing_city_id")
	var region_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "region_id", "region_id")
	var paid_total_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "paid_total_amount", "paid_total_amount")
	var breakdown_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "breakdown_amount", "breakdown_amount")
	var additive_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "mult.additive", "additive")
	var multiplicative_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "mult.multiplicative", "multiplicative")
	var base_steps_label = _translate_field(EVENT_TYPE_SYNERGY_TOLL, "detail", "mult.base_steps", "base_steps")

	assert_str(details).contains(landing_city_label + ": c1")
	assert_str(details).contains(region_label + ": r1")
	assert_str(details).contains(paid_total_label + ": 8")
	assert_str(details).contains(breakdown_label + "[c1]: 3")
	assert_str(details).contains(breakdown_label + "[c2]: 5")
	assert_str(details).contains(additive_label + ":")
	assert_str(details).contains(multiplicative_label + ":")
	assert_str(details).contains("breakdown[c1] " + base_steps_label + ": 2")
