extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _last_emitted_type := ""
var _events: Array = []

func before() -> void:
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
    _events = []

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

func _hud() -> Node:
    var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(hud))
    await get_tree().process_frame
    return hud

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
func test_hud_records_sanguo_events_to_toast_and_log_panel() -> void:
    var hud = await _hud()
    var toast_label: Label = hud.get_node("EventToast/Panel/Label")
    var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

    _bus.PublishSimple("core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
    await get_tree().process_frame
    _bus.PublishSimple("core.sanguo.dice.rolled", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Value\":6}")
    await get_tree().process_frame

    assert_str(toast_label.text).contains("core.sanguo.dice.rolled")
    assert_str(toast_label.text).contains("value=6")

    assert_int(log_list.get_item_count()).is_greater(0)
    var last := log_list.get_item_text(log_list.get_item_count() - 1)
    assert_str(last).contains("core.sanguo.dice.rolled")

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

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":123,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 123")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p1\",\"Money\":456,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 456")

    _bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"PlayerId\":\"p2\",\"Money\":999,\"PositionIndex\":0}")
    await get_tree().process_frame
    assert_str(money_label.text).is_equal("Money: 456")

# ACC:T9.2
func test_dice_button_emits_ui_roll_event() -> void:
    var hud = await _hud()
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    _last_emitted_type = ""
    dice.emit_signal("pressed")
    await get_tree().process_frame
    assert_str(_last_emitted_type).is_equal("ui.hud.dice.roll")

# ACC:T17.10
func test_hud_dice_roll_triggers_core_dice_event_with_trace_ids() -> void:
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

    var core_evt := _last_event("core.sanguo.dice.rolled")
    assert_bool(core_evt.size() > 0).is_true()
    var core_payload: Dictionary = JSON.parse_string(str(core_evt.get("data_json", "{}")))
    assert_str(str(core_payload.get("PlayerId", ""))).is_equal("p1")
    assert_int(int(core_payload.get("Value", 0))).is_between(1, 6)
    assert_str(str(core_payload.get("CorrelationId", ""))).is_equal(corr)
    assert_str(str(core_payload.get("CausationId", ""))).is_equal("ui.hud.dice.roll")

# ACC:T17.4
# ACC:T17.15
func test_money_cap_overflow_writes_security_audit_and_toast_auto_hides_after_3_seconds() -> void:
    var hud = await _hud()
    var toast: Control = hud.get_node("EventToast")
    var toast_label: Label = hud.get_node("EventToast/Panel/Label")
    var audit_before := _read_security_audit_text()

    assert_float(float(toast.AutoHideSeconds)).is_equal(3.0)
    toast.AutoHideSeconds = 0.05

    _bus.PublishSimple(
        "core.sanguo.city.toll.paid",
        "ut",
        "{\"GameId\":\"g1\",\"PayerId\":\"p1\",\"OwnerId\":\"o1\",\"CityId\":\"c1\",\"Amount\":10,\"OwnerAmount\":1,\"TreasuryOverflow\":9}"
    )
    await get_tree().process_frame

    for _i in range(30):
        if toast.visible:
            break
        await get_tree().process_frame
    assert_bool(toast.visible).is_true()
    assert_str(toast_label.text).contains("core.sanguo.city.toll.paid")
    assert_str(toast_label.text).contains("city=c1")
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

    assert_int(after_lines.size()).is_equal(before_lines.size() + 1)
    var last_line: String = str(after_lines[after_lines.size() - 1])
    var parsed = JSON.parse_string(last_line)
    assert_bool(parsed is Dictionary).is_true()
    var obj: Dictionary = parsed
    assert_bool(obj.has("ts")).is_true()
    assert_bool(obj.has("action")).is_true()
    assert_bool(obj.has("reason")).is_true()
    assert_bool(obj.has("target")).is_true()
    assert_bool(obj.has("caller")).is_true()
    assert_str(str(obj.get("action", ""))).is_equal("SANGUO_MONEY_CAPPED")
    assert_str(str(obj.get("reason", ""))).is_equal("money_cap_overflow")
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
