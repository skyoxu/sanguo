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

func _translate_summary(event_type: String) -> String:
    var summary_key := "ui.hud.event.%s.summary" % event_type
    var text := _try_translate(summary_key)
    if text.length() > 0:
        return text
    var title_key := "ui.hud.event.%s.title" % event_type
    text = _try_translate(title_key)
    if text.length() > 0:
        return text
    var shared_key := "ui.hud.event.shared.summary.unknown"
    text = _try_translate(shared_key)
    if text.length() > 0:
        return text
    return "event"

func test_event_log_details_panel_shows_toll_paid_facts_and_deltas() -> void:
    var original_locale := _set_locale("zh")
    var hud = await _hud()
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
    var details: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")

    log_list.clear()
    details.text = ""

    _bus.PublishSimple(
        "core.sanguo.city.toll.paid",
        "ut",
        "{\"GameId\":\"g1\",\"TurnNumber\":1,\"PayerId\":\"p1\",\"OwnerId\":\"o1\",\"CityId\":\"tile_01\",\"Amount\":10,\"OwnerAmount\":1,\"TreasuryOverflow\":9,\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":1,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":1,\"RegionStepDelta\":0,\"EffectiveSteps\":4,\"Sources\":18}}"
    )

    for _i in range(10):
        await get_tree().process_frame
        if log_list.get_item_count() > 0 and str(details.text).length() > 0:
            break

    assert_int(log_list.get_item_count()).is_equal(1)
    var summary_label := _translate_summary("core.sanguo.city.toll.paid")
    assert_str(log_list.get_item_text(0)).contains(summary_label)
    assert_str(log_list.get_item_text(0)).not_contains("core.sanguo.city.toll.paid")
    var deltas_label := _translate_field("core.sanguo.city.toll.paid", "detail", "deltas", "deltas")
    assert_str(str(details.text)).contains(deltas_label + ":")

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

    var city_label := _translate_field("core.sanguo.city.toll.paid", "detail", "city_id", "city_id")
    var city_name := _try_translate("tile.map001.tile_01.name")
    assert_bool(city_name.strip_edges().length() > 0).is_true()
    assert_str(str(details.text)).contains(city_label + ": " + city_name)
    assert_str(str(details.text)).contains(money_label + "[p1]: -10")
    assert_str(str(details.text)).contains(money_label + "[o1]: +1")
    assert_str(str(details.text)).contains(treasury_label + ": +9")

    var additive_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.additive", "additive")
    var multiplicative_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.multiplicative", "multiplicative")
    var base_steps_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.base_steps", "base_steps")
    var building_delta_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.building_step_delta", "building_step_delta")
    var relic_delta_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.relic_step_delta", "relic_step_delta")
    var effective_steps_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.effective_steps", "effective_steps")
    var effective_multiplier_label := _translate_field("core.sanguo.city.toll.paid", "detail", "mult.effective_multiplier", "effective_multiplier")

    assert_str(str(details.text)).contains(additive_label + ":")
    assert_str(str(details.text)).contains(base_steps_label + ": 2")
    assert_str(str(details.text)).contains(building_delta_label + ": +1")
    assert_str(str(details.text)).contains(relic_delta_label + ": +1")

    assert_str(str(details.text)).contains(multiplicative_label + ":")
    assert_str(str(details.text)).contains(effective_steps_label + ": 4")
    assert_str(str(details.text)).contains(effective_multiplier_label + ": 2")

    _restore_locale(original_locale)
