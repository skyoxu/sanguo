extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node

func before() -> void:
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func _hud() -> Node:
    var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(hud))
    await get_tree().process_frame
    return hud

func test_event_log_details_panel_shows_toll_paid_facts_and_deltas() -> void:
    var hud = await _hud()
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
    var details: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")

    log_list.clear()
    details.text = ""

    _bus.PublishSimple(
        "core.sanguo.city.toll.paid",
        "ut",
        "{\"GameId\":\"g1\",\"TurnNumber\":1,\"PayerId\":\"p1\",\"OwnerId\":\"o1\",\"CityId\":\"c1\",\"Amount\":10,\"OwnerAmount\":1,\"TreasuryOverflow\":9}"
    )

    for _i in range(10):
        await get_tree().process_frame
        if log_list.get_item_count() > 0 and str(details.text).length() > 0:
            break

    assert_int(log_list.get_item_count()).is_equal(1)
    assert_str(log_list.get_item_text(0)).contains("core.sanguo.city.toll.paid")
    assert_str(str(details.text)).contains("deltas:")

    var money_key := "ui.hud.event.core.sanguo.city.toll.paid.delta.money_delta"
    var treasury_key := "ui.hud.event.core.sanguo.city.toll.paid.delta.treasury_delta"
    var money_label := "money_delta"
    var treasury_label := "treasury_delta"

    if TranslationServer.has_method("translate"):
        var m := String(TranslationServer.translate(money_key))
        if m.strip_edges().length() > 0 and m != money_key:
            money_label = m
        var t := String(TranslationServer.translate(treasury_key))
        if t.strip_edges().length() > 0 and t != treasury_key:
            treasury_label = t

    assert_str(str(details.text)).contains(money_label + "[p1]: -10")
    assert_str(str(details.text)).contains(money_label + "[o1]: +1")
    assert_str(str(details.text)).contains(treasury_label + ": +9")
