extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_YEAR_PRICE_ADJUSTED = "core.sanguo.economy.year.price.adjusted"

var _bus: Node
var _last_data_json = ""

func before() -> void:
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
	_last_data_json = ""

func _on_domain_event_emitted(_type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	_last_data_json = str(data_json)

func _hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

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

func _publish_year_price_adjusted(data_json: String) -> void:
	_bus.PublishSimple(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "ut", data_json)


# ACC:T51.5
# Money-related economy events must be visible in the HUD event log with applied multiplier context.
func test_task51_event_log_includes_year_price_adjusted_details() -> void:
	var hud = await _hud()

	_publish_year_price_adjusted("{\"GameId\":\"g1\",\"TurnNumber\":10,\"Year\":3,\"CityId\":\"c9\",\"OldPrice\":100,\"NewPrice\":130,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":0}}")
	await get_tree().process_frame

	assert_str(_last_data_json).contains("AppliedMultipliers")
	var msgs = _event_log_messages(hud)
	assert_int(msgs.size()).is_greater_equal(1)
	var last = str(msgs[msgs.size() - 1])
	assert_str(last).contains(EVENT_TYPE_YEAR_PRICE_ADJUSTED)
	assert_str(last).contains("mult=1.5")

	var details = _event_log_details(hud)
	var city_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "city_id", "city_id")
	var year_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "year", "year")
	var old_price_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "old_price", "old_price")
	var new_price_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "new_price", "new_price")
	var additive_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "mult.additive", "additive")
	var multiplicative_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "mult.multiplicative", "multiplicative")
	var effective_multiplier_label = _translate_field(EVENT_TYPE_YEAR_PRICE_ADJUSTED, "detail", "mult.effective_multiplier", "effective_multiplier")

	assert_str(details).contains(city_label + ": c9")
	assert_str(details).contains(year_label + ": 3")
	assert_str(details).contains(old_price_label + ": 100")
	assert_str(details).contains(new_price_label + ": 130")
	assert_str(details).contains(additive_label + ":")
	assert_str(details).contains(multiplicative_label + ":")
	assert_str(details).contains(effective_multiplier_label + ": 1.5")
