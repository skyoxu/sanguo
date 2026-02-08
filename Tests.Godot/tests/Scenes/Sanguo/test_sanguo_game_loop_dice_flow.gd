extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_DICE_ROLL := "ui.hud.dice.roll"
const CORE_DICE_ROLLED := "core.sanguo.dice.rolled"
const CORE_TOKEN_MOVED := "core.sanguo.board.token.moved"
const CORE_AI_DECISION_MADE := "core.sanguo.ai.decision.made"

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

func _has_turn_started_for(active_player_id: String) -> bool:
    for e in _events_of_type("core.sanguo.game.turn.started"):
        var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
        if str(payload.get("ActivePlayerId", "")) == active_player_id:
            return true
    return false

func _find_turn_started_index_for(active_player_id: String, start_index: int = 0) -> int:
    for i in range(max(0, start_index), _events.size()):
        var e: Dictionary = _events[i]
        if str(e.get("type", "")) != "core.sanguo.game.turn.started":
            continue
        var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
        if str(payload.get("ActivePlayerId", "")) == active_player_id:
            return i
    return -1

func _wait_for_turn_started(active_player_id: String, max_frames: int = 180) -> void:
    for _i in range(max_frames):
        if _has_turn_started_for(active_player_id):
            return
        await get_tree().process_frame
    if not _has_turn_started_for(active_player_id):
        var seen: Array = []
        for e in _events_of_type("core.sanguo.game.turn.started"):
            var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
            seen.append(str(payload.get("ActivePlayerId", "")))
        var types: Array = []
        for e in _events:
            types.append(str(e.get("type", "")))
        print("Missing turn.started for '%s'. Seen ActivePlayerId values: %s" % [active_player_id, str(seen)])
        print("Observed event types: %s" % str(types))
    assert_bool(_has_turn_started_for(active_player_id)).is_true()

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

func _resolve_hud(main: Node) -> Node:
    if main == null:
        return null

    var hud := main.get_node_or_null("HUD")
    if hud != null:
        return hud

    hud = main.get_node_or_null("SplitRoot/TopArea/HudLayer/HUD")
    if hud != null:
        return hud

    return get_node_or_null("/root/Main/SplitRoot/TopArea/HudLayer/HUD")

# Acceptance anchors:
# ACC:T17.10
func test_ui_dice_roll_produces_core_dice_and_token_move_with_order_and_trace_ids() -> void:
    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame

    var controller := main.get_node_or_null("SanguoGameLoopController")
    if controller != null:
        controller.set("AiAutoAdvanceDelaySeconds", 0.05)
        controller.set("AiAutoAdvanceDelaySecondsWhenSkip", 0.05)

    _bus.PublishSimple("ui.menu.start", "ut", "{}")
    await _wait_for_event("core.sanguo.game.turn.started", 180)

    var hud := _resolve_hud(main)
    assert_bool(hud != null).is_true()
    var dice: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")
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

    # The human turn now waits for an explicit tile action selection (or Skip) before advancing.
    var to_index := int(core_move_payload.get("ToIndex", 0))
    _bus.PublishSimple("ui.sanguo.tile.action.selected", "ut",
        "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"ToIndex\":%d,\"Action\":\"skip\",\"CorrelationId\":\"%s\",\"CausationId\":\"ui.sanguo.tile.action.selected\"}" % [to_index, corr])

    await _wait_for_event("core.sanguo.game.turn.advanced", 180)
    await _wait_for_turn_started("ai-1", 180)

    _events = []
    var corr2 := "corr-ai"
    _bus.PublishSimple(UI_DICE_ROLL, "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"ai-1\",\"CorrelationId\":\"%s\",\"CausationId\":\"%s\"}" % [corr2, UI_DICE_ROLL])
    for _i in range(30):
        await get_tree().process_frame

    var core_dice2_evt := _find_last_event_for_corr_player(CORE_DICE_ROLLED, corr2, UI_DICE_ROLL, "ai-1")
    assert_bool(core_dice2_evt.size() == 0).is_true()
    var core_move2_evt := _find_last_event_for_corr_player(CORE_TOKEN_MOVED, corr2, UI_DICE_ROLL, "ai-1")
    assert_bool(core_move2_evt.size() == 0).is_true()


# ACC:T60.4
func test_ai_auto_advance_is_not_blocked_by_ai_result_popup_pause() -> void:
    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame

    var controller := main.get_node_or_null("SanguoGameLoopController")
    if controller != null:
        controller.set("AiAutoAdvanceDelaySeconds", 2.0)
        controller.set("AiAutoAdvanceDelaySecondsWhenSkip", 2.0)

    var hud := _resolve_hud(main)
    assert_bool(hud != null).is_true()
    var popup: Control = hud.get_node("EventResultPopup")
    popup.AutoHideSeconds = 1.2

    _bus.PublishSimple("ui.menu.start", "ut", "{}")
    await _wait_for_event("core.sanguo.game.turn.started", 180)
    var initial_turn_started_count := _events_of_type("core.sanguo.game.turn.started").size()
    assert_int(initial_turn_started_count).is_greater_equal(1)

    _events = []
    var dice: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")
    dice.emit_signal("pressed")

    await _wait_for_event(UI_DICE_ROLL, 120)
    var ui_evt := _last_event(UI_DICE_ROLL)
    var ui_payload: Dictionary = JSON.parse_string(str(ui_evt.get("data_json", "{}")))
    var corr := str(ui_payload.get("CorrelationId", ""))
    assert_bool(corr.length() > 0).is_true()

    await _wait_for_event_for_corr_player(CORE_TOKEN_MOVED, corr, UI_DICE_ROLL, "p1", 180)
    var move_evt := _find_last_event_for_corr_player(CORE_TOKEN_MOVED, corr, UI_DICE_ROLL, "p1")
    var move_payload: Dictionary = JSON.parse_string(str(move_evt.get("data_json", "{}")))
    var to_index := int(move_payload.get("ToIndex", 0))

    _bus.PublishSimple("ui.sanguo.tile.action.selected", "ut",
        "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"ToIndex\":%d,\"Action\":\"skip\",\"CorrelationId\":\"%s\",\"CausationId\":\"ui.sanguo.tile.action.selected\"}" % [to_index, corr])

    var elapsed_begin := Time.get_ticks_msec()
    var saw_paused := false
    for _i in range(240):
        if get_tree().paused:
            saw_paused = true
            break
        await get_tree().process_frame
    assert_bool(saw_paused).is_true()

    var p1_turn_index := -1
    for _i in range(420):
        p1_turn_index = _find_turn_started_index_for("p1", 0)
        if p1_turn_index >= 0:
            break
        await get_tree().process_frame

    var final_turn_started_count := _events_of_type("core.sanguo.game.turn.started").size()

    if p1_turn_index < 0 or final_turn_started_count <= initial_turn_started_count:
        var types: Array = []
        for e in _events:
            types.append(str(e.get("type", "")))
        print("AI popup recovery missing next p1 turn. Observed event types: %s" % str(types))

    assert_bool(final_turn_started_count > initial_turn_started_count).is_true()

    var elapsed_seconds := float(Time.get_ticks_msec() - elapsed_begin) / 1000.0
    assert_float(elapsed_seconds).is_less(8.0)
