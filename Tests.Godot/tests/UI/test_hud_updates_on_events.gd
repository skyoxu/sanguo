extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

var _last_emitted_type := ""
var _events: Array = []

func before_test() -> void:
    await _setup_event_bus()
    _connect_domain_event_emitted(Callable(self, "_on_domain_event_emitted"))
    _last_emitted_type = ""
    _events = []

func after_test() -> void:
    await _teardown_event_bus()

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
    _last_emitted_type = str(type)
    _events.append({"type": str(type), "data_json": str(data_json)})

func _security_audit_path() -> String:
    return ProjectSettings.globalize_path("user://logs/security/security-audit.jsonl")

func _read_security_audit_text() -> String:
    var path := _security_audit_path()
    if not FileAccess.file_exists(path):
        return ""
    var f := FileAccess.open(path, FileAccess.READ)
    return f.get_as_text()

func _last_event(type_name: String) -> Dictionary:
    for i in range(_events.size() - 1, -1, -1):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) == type_name:
            return e
    return {}

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

# ACC:T22.2
func test_hud_core_interactions_are_wired() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")

# ACC:T20.2
# ACC:T9.4
func test_hud_has_core_status_nodes() -> void:
    var hud = await _hud()
    assert_object(hud.get_node_or_null("TopBar/HBox/DiceButton")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/ActivePlayerLabel")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/DateLabel")).is_not_null()
    assert_object(hud.get_node_or_null("TopBar/HBox/MoneyLabel")).is_not_null()

# ACC:T9.5
func test_hud_has_event_toast_and_log_panel_nodes() -> void:
    var hud = await _hud()
    assert_object(hud.get_node_or_null("EventToast")).is_not_null()
    assert_object(hud.get_node_or_null("EventLogPanel")).is_not_null()

# ACC:T9.6
# ACC:T19.2
func test_hud_records_sanguo_events_to_toast_and_log_panel() -> void:
    var hud = await _hud()
    var toast_label: Label = hud.get_node("EventToast/Panel/Label")
    var toast: Control = hud.get_node("EventToast")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    assert_bool(toast.visible).is_false()

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    # Clear the toast visibility so we can deterministically assert the next event shows it.
    toast.visible = false

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame

    assert_bool(toast.visible).is_true()
    var summary_label := _translate_summary("core.sanguo.dice.rolled")
    var value_label := _translate_field("core.sanguo.dice.rolled", "detail", "value", "value")
    assert_str(toast_label.text).contains(summary_label)
    assert_str(toast_label.text).contains(value_label + "=6")
    assert_str(toast_label.text).not_contains("core.sanguo.dice.rolled")

    assert_int(log_list.get_item_count()).is_greater(0)
    var last := log_list.get_item_text(log_list.get_item_count() - 1)
    assert_str(last).contains(summary_label)
    assert_str(last).not_contains("core.sanguo.dice.rolled")

func test_hud_records_month_season_game_end_events_to_toast_and_log_panel() -> void:
    var hud = await _hud()
    var toast_label: Label = hud.get_node("EventToast/Panel/Label")
    var toast: Control = hud.get_node("EventToast")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    var cases := [
        {"type": "core.sanguo.board.token.moved", "json": "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":3,\"Steps\":3,\"PassedStart\":false}"},
        {"type": "core.sanguo.city.bought", "json": "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"c1\",\"Price\":100}"},
        {"type": "core.sanguo.economy.month.settled", "json": "{\"GameId\":\"g1\",\"Year\":3,\"Month\":2,\"PlayerSettlements\":[]}"},
        {"type": "core.sanguo.economy.season.event.applied", "json": "{\"GameId\":\"g1\",\"Year\":3,\"Season\":\"Spring\",\"YieldMultiplier\":1.0,\"AffectedRegionIds\":[]}"},
        {"type": "core.sanguo.game.ended", "json": "{\"GameId\":\"g1\",\"EndReason\":\"test\"}"},
        {"type": "core.sanguo.game.turn.advanced", "json": "{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":2,\"Year\":3,\"Month\":2,\"Day\":2}"},
    ]

    for c in cases:
        toast.visible = false
        toast_label.text = ""
        log_list.clear()

        _bus.PublishSimple(str(c["type"]), "ut", str(c["json"]))
        for _i in range(10):
            await get_tree().process_frame
            if toast.visible and log_list.get_item_count() > 0:
                break

        assert_bool(toast.visible).is_true()
        assert_bool(toast_label.text.length() > 0).is_true()
        var summary_label := _translate_summary(str(c["type"]))
        assert_str(toast_label.text).contains(summary_label)
        assert_str(toast_label.text).not_contains(str(c["type"]))

        assert_int(log_list.get_item_count()).is_greater(0)
        var last := log_list.get_item_text(log_list.get_item_count() - 1)
        assert_str(last).contains(summary_label)
        assert_str(last).not_contains(str(c["type"]))

func test_hud_updates_on_score_event() -> void:
    var hud = await _hud()
    var score_label: Label = hud.get_node("TopBar/HBox/ScoreLabel")
    _bus.PublishSimple("core.score.updated", "ut", "{\"value\":42}")
    await get_tree().process_frame
    assert_str(score_label.text).is_equal("Score: 42")

func test_hud_updates_on_health_event() -> void:
    var hud = await _hud()
    var hp_label: Label = hud.get_node("TopBar/HBox/HealthLabel")
    _bus.PublishSimple("core.health.updated", "ut", "{\"value\":77}")
    await get_tree().process_frame
    assert_str(hp_label.text).is_equal("HP: 77")

# ACC:T20.3
# ACC:T21.2
func test_hud_updates_on_sanguo_turn_started_event() -> void:
    var hud = await _hud()
    var active_label: Label = hud.get_node("TopBar/HBox/ActivePlayerLabel")
    var date_label: Label = hud.get_node("TopBar/HBox/DateLabel")
    var money_label: Label = hud.get_node("TopBar/HBox/MoneyLabel")

    assert_str(money_label.text).is_equal("Money: -")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    assert_str(active_label.text).is_equal("Player: p1")
    assert_str(date_label.text).is_equal("Date: 0003-02-01")

    _bus.PublishSimple("core.sanguo.game.turn.advanced", "ut", "{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":2,\"Year\":3,\"Month\":2,\"Day\":2}")
    await get_tree().process_frame
    assert_str(date_label.text).is_equal("Date: 0003-02-02")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":123,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 123")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":456,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 456")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p2\",\"Money\":999,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 456")

func test_hud_ignores_state_changed_before_turn_started() -> void:
    var hud = await _hud()
    var money_label: Label = hud.get_node("TopBar/HBox/MoneyLabel")

    assert_str(money_label.text).is_equal("Money: -")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":111,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: -")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":222,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 222")

# ACC:T9.2
func test_dice_button_emits_ui_roll_event() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    _last_emitted_type = ""
    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    dice.emit_signal("pressed")
    await get_tree().process_frame
    assert_str(_last_emitted_type).is_equal("ui.hud.dice.roll")

# The HUD is responsible for emitting the UI command with trace ids.
# Core domain events are validated in an integration test that includes the game loop controller.
func test_hud_dice_roll_emits_ui_event_with_trace_ids() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    _events = []

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame

    dice.emit_signal("pressed")
    for _i in range(10):
        await get_tree().process_frame

    var ui_evt := _last_event("ui.hud.dice.roll")
    assert_bool(ui_evt.size() > 0).is_true()
    var ui_payload: Dictionary = JSON.parse_string(str(ui_evt.get("data_json", "{}")))
    assert_str(str(ui_payload.get("PlayerId", ""))).is_equal("p1")
    assert_str(str(ui_payload.get("CausationId", ""))).is_equal("ui.hud.dice.roll")
    var corr := str(ui_payload.get("CorrelationId", ""))
    assert_bool(corr.length() > 0).is_true()

# ACC:T17.4
# ACC:T17.15
func test_money_cap_overflow_writes_security_audit_and_toast_auto_hides_after_3_seconds() -> void:
    var original_locale := _set_locale("zh")
    var hud = await _hud()
    var toast: Control = hud.get_node("EventToast")
    var toast_label: Label = hud.get_node("EventToast/Panel/Label")
    var audit_before := _read_security_audit_text()

    assert_float(float(toast.AutoHideSeconds)).is_equal(3.0)
    toast.AutoHideSeconds = 0.05

    _bus.PublishSimple(
        "core.sanguo.city.toll.paid",
        "ut",
        "{\"GameId\":\"g1\",\"PayerId\":\"p1\",\"OwnerId\":\"o1\",\"CityId\":\"tile_01\",\"Amount\":10,\"OwnerAmount\":1,\"TreasuryOverflow\":9}"
    )
    await get_tree().process_frame

    for _i in range(30):
        if toast.visible:
            break
        await get_tree().process_frame
    assert_bool(toast.visible).is_true()
    var summary_label := _translate_summary("core.sanguo.city.toll.paid")
    var city_label := _translate_field("core.sanguo.city.toll.paid", "detail", "city_id", "city")
    var city_name := _try_translate("tile.map001.tile_01.name")
    assert_bool(city_name.strip_edges().length() > 0).is_true()
    assert_str(toast_label.text).contains(summary_label)
    assert_str(toast_label.text).contains(city_label + "=" + city_name)
    assert_str(toast_label.text).not_contains("core.sanguo.city.toll.paid")
    var shown_ms: int = Time.get_ticks_msec()

    var before_lines: Array = []
    for line in audit_before.split("\n"):
        var t := str(line).strip_edges()
        if not t.is_empty():
            before_lines.append(t)

    var audit_after := _read_security_audit_text()
    var after_lines: Array = []
    for line in audit_after.split("\n"):
        var t := str(line).strip_edges()
        if not t.is_empty():
            after_lines.append(t)

    assert_int(after_lines.size()).is_greater_equal(before_lines.size() + 1)
    var new_lines: Array = []
    for i in range(before_lines.size(), after_lines.size()):
        new_lines.append(after_lines[i])

    var found := false
    var obj: Dictionary = {}
    for line in new_lines:
        var parsed = JSON.parse_string(str(line))
        if parsed is Dictionary:
            var parsed_obj: Dictionary = parsed
            if str(parsed_obj.get("action", "")) == "SANGUO_MONEY_CAPPED" and str(parsed_obj.get("reason", "")) == "money_cap_overflow":
                found = true
                obj = parsed_obj
                break

    assert_bool(found).is_true()
    assert_bool(obj.has("ts")).is_true()
    assert_bool(obj.has("action")).is_true()
    assert_bool(obj.has("reason")).is_true()
    assert_bool(obj.has("target")).is_true()
    assert_bool(obj.has("caller")).is_true()
    assert_bool(str(obj.get("target", "")).length() > 0).is_true()
    assert_bool(str(obj.get("caller", "")).length() > 0).is_true()

    assert_bool(hud.is_inside_tree()).is_true()
    assert_bool(hud.visible).is_true()
    assert_object(get_tree().get_root().find_child("GameOver", true, false)).is_null()
    assert_object(get_tree().get_root().find_child("Error", true, false)).is_null()

    for _i in range(240):
        if not toast.visible:
            break
        await get_tree().process_frame
    assert_bool(toast.visible).is_false()
    var elapsed_ms: int = int(Time.get_ticks_msec() - shown_ms)
    assert_int(elapsed_ms).is_less_equal(3000)

    _restore_locale(original_locale)

# ACC:T22.3
func test_hud_updates_on_sanguo_dice_rolled_event() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":1}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 1")

func test_hud_does_not_mix_dice_results_between_players() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p2\",\"Value\":1}")
    await get_tree().process_frame
    assert_str(dice.text).is_equal("Dice: 6")




# ACC:T24.2

func test_event_log_updates_when_core_event_is_emitted() -> void:

    var hud = await _hud()

    var log_panel: Control = hud.get_node("EventLogPanel")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    log_list.clear()
    assert_bool(log_panel.visible).is_false()



    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")

    for _i in range(10):

        await get_tree().process_frame

        if log_list.get_item_count() > 0:

            break



    assert_int(log_list.get_item_count()).is_equal(1)

    var summary_label := _translate_summary("core.sanguo.dice.rolled")
    assert_str(log_list.get_item_text(0)).contains(summary_label)
    assert_str(log_list.get_item_text(0)).not_contains("core.sanguo.dice.rolled")

    hud.call("ToggleEventLogOverlay")
    await get_tree().process_frame
    assert_bool(log_panel.is_visible_in_tree()).is_true()
    assert_bool(log_list.is_visible_in_tree()).is_true()



# ACC:T24.3

func test_event_log_appends_entries_and_keeps_history_in_session() -> void:

    var hud = await _hud()

    var log_panel: Control = hud.get_node("EventLogPanel")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    log_list.clear()
    assert_bool(log_panel.visible).is_false()

    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{not-json")
    for _i in range(10):
        await get_tree().process_frame
    assert_int(log_list.get_item_count()).is_equal(0)


    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")

    for _i in range(10):

        await get_tree().process_frame

        if log_list.get_item_count() == 1:

            break

    assert_int(log_list.get_item_count()).is_equal(1)

    var first := log_list.get_item_text(0)



    _bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"c1\",\"Price\":100}")

    for _i in range(10):

        await get_tree().process_frame

        if log_list.get_item_count() == 2:

            break



    assert_int(log_list.get_item_count()).is_equal(2)

    assert_str(log_list.get_item_text(0)).is_equal(first)

    var city_summary_label := _translate_summary("core.sanguo.city.bought")
    assert_str(log_list.get_item_text(1)).contains(city_summary_label)
    assert_str(log_list.get_item_text(1)).not_contains("core.sanguo.city.bought")

    hud.call("ToggleEventLogOverlay")
    await get_tree().process_frame
    assert_bool(log_panel.is_visible_in_tree()).is_true()
    assert_bool(log_list.is_visible_in_tree()).is_true()



# ACC:T24.4

func test_event_log_entry_order_matches_event_emission_order() -> void:

    var hud = await _hud()

    var log_panel: Control = hud.get_node("EventLogPanel")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    log_list.clear()
    assert_bool(log_panel.visible).is_false()



    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")

    _bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"c1\",\"Price\":100}")

    for _i in range(10):

        await get_tree().process_frame

        if log_list.get_item_count() == 2:

            break



    assert_int(log_list.get_item_count()).is_equal(2)

    var dice_summary_label := _translate_summary("core.sanguo.dice.rolled")
    assert_str(log_list.get_item_text(0)).contains(dice_summary_label)
    assert_str(log_list.get_item_text(0)).not_contains("core.sanguo.dice.rolled")

    var city_summary_label := _translate_summary("core.sanguo.city.bought")
    assert_str(log_list.get_item_text(1)).contains(city_summary_label)
    assert_str(log_list.get_item_text(1)).not_contains("core.sanguo.city.bought")

    hud.call("ToggleEventLogOverlay")
    await get_tree().process_frame
    assert_bool(log_panel.is_visible_in_tree()).is_true()
    assert_bool(log_list.is_visible_in_tree()).is_true()



# ACC:T24.5

func test_event_log_entries_contain_player_facing_summary_fields() -> void:

    var original_locale := _set_locale("zh")
    var hud = await _hud()

    var log_panel: Control = hud.get_node("EventLogPanel")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    log_list.clear()
    assert_bool(log_panel.visible).is_false()



    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")

    _bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":100}")

    for _i in range(10):

        await get_tree().process_frame

        if log_list.get_item_count() == 2:

            break



    assert_int(log_list.get_item_count()).is_equal(2)

    var a := log_list.get_item_text(0)

    var b := log_list.get_item_text(1)



    var dice_summary_label := _translate_summary("core.sanguo.dice.rolled")
    var value_label := _translate_field("core.sanguo.dice.rolled", "detail", "value", "value")
    assert_str(a).contains(dice_summary_label)
    assert_str(a).contains(value_label + "=6")
    assert_str(a).not_contains("core.sanguo.dice.rolled")

    var city_summary_label := _translate_summary("core.sanguo.city.bought")
    var city_label := _translate_field("core.sanguo.city.bought", "detail", "city_id", "city")
    var price_label := _translate_field("core.sanguo.city.bought", "detail", "price", "price")
    var city_name := _try_translate("tile.map001.tile_01.name")
    assert_bool(city_name.strip_edges().length() > 0).is_true()
    assert_str(b).contains(city_summary_label)
    assert_str(b).contains(city_label + "=" + city_name)
    assert_str(b).contains(price_label + "=100")
    assert_str(b).not_contains("core.sanguo.city.bought")

    assert_str(a).is_not_equal(b)

    hud.call("ToggleEventLogOverlay")
    await get_tree().process_frame
    assert_bool(log_panel.is_visible_in_tree()).is_true()
    assert_bool(log_list.is_visible_in_tree()).is_true()

    _restore_locale(original_locale)

