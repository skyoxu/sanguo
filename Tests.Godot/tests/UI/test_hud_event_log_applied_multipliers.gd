extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _last_data_json := ""

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

func _publish_city_bought(data_json: String) -> void:
    _bus.PublishSimple("core.sanguo.city.bought", "ut", data_json)

func test_event_log_shows_effective_multiplier_but_hides_breakdown_when_sources_none() -> void:
    var hud = await _hud()

    _publish_city_bought("{\"CityId\":\"c1\",\"Price\":50,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":0}}")
    await get_tree().process_frame

    assert_str(_last_data_json).contains("AppliedMultipliers")

    var msgs := _event_log_messages(hud)
    assert_int(msgs.size()).is_greater_equal(1)
    var last := str(msgs[msgs.size() - 1])
    assert_str(last).contains("core.sanguo.city.bought")
    assert_str(last).contains("mult=1.5")
    assert_str(last).not_contains(" c=")
    assert_str(last).not_contains(" b=")
    assert_str(last).not_contains(" e=")
    assert_str(last).not_contains(" a=")

func test_event_log_can_show_breakdown_when_sources_provided() -> void:
    var hud = await _hud()

    _publish_city_bought("{\"CityId\":\"c1\",\"Price\":50,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":1,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":3,\"Sources\":1}}")
    await get_tree().process_frame

    assert_str(_last_data_json).contains("AppliedMultipliers")

    var msgs := _event_log_messages(hud)
    assert_int(msgs.size()).is_greater_equal(1)
    var last := str(msgs[msgs.size() - 1])
    assert_str(last).contains("mult=1.5")
