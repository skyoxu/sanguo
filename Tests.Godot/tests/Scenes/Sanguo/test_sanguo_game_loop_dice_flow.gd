extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_DICE_ROLL := "ui.hud.dice.roll"
const CORE_DICE_ROLLED := "core.sanguo.dice.rolled"
const CORE_TOKEN_MOVED := "core.sanguo.board.token.moved"

var _bus: Node
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
    _events.append({"type": str(type), "data_json": str(data_json)})

func _last_event(type_name: String) -> Dictionary:
    for i in range(_events.size() - 1, -1, -1):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) == type_name:
            return e
    return {}

func _find_first_index(type_name: String) -> int:
    for i in range(_events.size()):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) == type_name:
            return i
    return -1

func _find_first_index_for_corr_player(type_name: String, correlation_id: String, causation_id: String, player_id: String) -> int:
    for i in range(_events.size()):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) != type_name:
            continue
        var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
        if str(payload.get("CorrelationId", "")) == correlation_id and str(payload.get("CausationId", "")) == causation_id and str(payload.get("PlayerId", "")) == player_id:
            return i
    return -1

func _find_last_event_for_corr_player(type_name: String, correlation_id: String, causation_id: String, player_id: String) -> Dictionary:
    for i in range(_events.size() - 1, -1, -1):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) != type_name:
            continue
        var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
        if str(payload.get("CorrelationId", "")) == correlation_id and str(payload.get("CausationId", "")) == causation_id and str(payload.get("PlayerId", "")) == player_id:
            return e
    return {}

func _events_of_type(type_name: String) -> Array:
    var out: Array = []
    for e in _events:
        if str(e.get("type", "")) == type_name:
            out.append(e)
    return out

func _wait_for_event(type_name: String, max_frames: int = 120) -> void:
    for _i in range(max_frames):
        if _last_event(type_name).size() > 0:
            return
        await get_tree().process_frame
    assert_bool(_last_event(type_name).size() > 0).is_true()

func _wait_for_event_for_corr_player(type_name: String, correlation_id: String, causation_id: String, player_id: String, max_frames: int = 120) -> void:
    for _i in range(max_frames):
        if _find_last_event_for_corr_player(type_name, correlation_id, causation_id, player_id).size() > 0:
            return
        await get_tree().process_frame
    assert_bool(_find_last_event_for_corr_player(type_name, correlation_id, causation_id, player_id).size() > 0).is_true()

# Acceptance anchors:
# ACC:T17.10
func test_ui_dice_roll_produces_core_dice_and_token_move_with_order_and_trace_ids() -> void:
    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame

    _bus.PublishSimple("ui.menu.start", "ut", "{}")
    await _wait_for_event("core.sanguo.game.turn.started", 180)

    var hud := main.get_node("HUD")
    var dice: Button = hud.get_node("TopBar/HBox/DiceButton")
    dice.emit_signal("pressed")

    await _wait_for_event(UI_DICE_ROLL, 120)

    var ui_evt := _last_event(UI_DICE_ROLL)
    var ui_payload: Dictionary = JSON.parse_string(str(ui_evt.get("data_json", "{}")))
    var corr := str(ui_payload.get("CorrelationId", ""))
    assert_bool(corr.length() > 0).is_true()

    await _wait_for_event_for_corr_player(CORE_DICE_ROLLED, corr, UI_DICE_ROLL, "p1", 180)
    await _wait_for_event_for_corr_player(CORE_TOKEN_MOVED, corr, UI_DICE_ROLL, "p1", 180)

    var core_dice_evt := _find_last_event_for_corr_player(CORE_DICE_ROLLED, corr, UI_DICE_ROLL, "p1")
    var core_dice_payload: Dictionary = JSON.parse_string(str(core_dice_evt.get("data_json", "{}")))
    assert_str(str(core_dice_payload.get("PlayerId", ""))).is_equal("p1")
    assert_int(int(core_dice_payload.get("Value", 0))).is_between(1, 6)
    assert_str(str(core_dice_payload.get("CorrelationId", ""))).is_equal(corr)
    assert_str(str(core_dice_payload.get("CausationId", ""))).is_equal(UI_DICE_ROLL)

    var core_move_evt := _find_last_event_for_corr_player(CORE_TOKEN_MOVED, corr, UI_DICE_ROLL, "p1")
    var core_move_payload: Dictionary = JSON.parse_string(str(core_move_evt.get("data_json", "{}")))
    assert_str(str(core_move_payload.get("PlayerId", ""))).is_equal("p1")
    assert_str(str(core_move_payload.get("CorrelationId", ""))).is_equal(corr)
    assert_str(str(core_move_payload.get("CausationId", ""))).is_equal(UI_DICE_ROLL)

    var dice_index := _find_first_index_for_corr_player(CORE_DICE_ROLLED, corr, UI_DICE_ROLL, "p1")
    var move_index := _find_first_index_for_corr_player(CORE_TOKEN_MOVED, corr, UI_DICE_ROLL, "p1")
    assert_int(dice_index).is_greater_equal(0)
    assert_int(move_index).is_greater_equal(0)
    assert_int(dice_index).is_less(move_index)

    var moved_for_corr := 0
    for e in _events_of_type(CORE_TOKEN_MOVED):
        var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
        if str(payload.get("CorrelationId", "")) == corr and str(payload.get("PlayerId", "")) == "p1":
            moved_for_corr += 1
    assert_int(moved_for_corr).is_equal(1)
