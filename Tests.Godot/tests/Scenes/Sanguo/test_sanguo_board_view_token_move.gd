extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TOKEN_MOVED := "core.sanguo.board.token.moved"
const EVENT_DICE_ROLLED := "core.sanguo.dice.rolled"

var _bus: Node

func _security_audit_path() -> String:
    return ProjectSettings.globalize_path("user://logs/security/security-audit.jsonl")

func _read_security_audit_text() -> String:
    var path := _security_audit_path()
    if not FileAccess.file_exists(path):
        return ""
    var f := FileAccess.open(path, FileAccess.READ)
    return f.get_as_text()

func _read_security_audit_lines() -> Array:
    var lines: Array = []
    for line in _read_security_audit_text().split("\n"):
        var t := str(line).strip_edges()
        if not t.is_empty():
            lines.append(t)
    return lines

func _assert_last_security_audit_entry_appended(before_lines: Array, expected_action: String, expected_reason: String) -> void:
    var after_lines := _read_security_audit_lines()
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
    assert_str(str(obj.get("action", ""))).is_equal(expected_action)
    assert_str(str(obj.get("reason", ""))).is_equal(expected_reason)
    assert_bool(str(obj.get("target", "")).length() > 0).is_true()
    assert_bool(str(obj.get("caller", "")).length() > 0).is_true()

func before() -> void:
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = load("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func _publish_move(player_id: String, to_index: int, data_json: String = "") -> void:
    var payload := data_json
    if payload.is_empty():
        payload = "{\"PlayerId\":\"%s\",\"ToIndex\":%d}" % [player_id, to_index]
    _bus.PublishSimple(EVENT_TOKEN_MOVED, "gdunit", payload)

func _publish_dice(player_id: String, value: int, data_json: String = "") -> void:
    var payload := data_json
    if payload.is_empty():
        payload = "{\"GameId\":\"g1\",\"PlayerId\":\"%s\",\"Value\":%d,\"CorrelationId\":\"corr\",\"CausationId\":\"cause\"}" % [player_id, value]
    _bus.PublishSimple(EVENT_DICE_ROLLED, "gdunit", payload)

func _target_position(view: Node, to_index: int) -> Vector2:
    return view.Origin + Vector2(float(to_index) * float(view.StepPixels), 0.0)

func _await_until(predicate: Callable, max_frames: int = 240) -> void:
    for _i in range(max_frames):
        if predicate.call():
            return
        await get_tree().process_frame
    assert_bool(predicate.call()).is_true()

# Acceptance anchors:
# ACC:T17.6
func test_board_view_total_positions_is_configured_by_scene() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    add_child(auto_free(view))
    await get_tree().process_frame
    assert_int(int(view.TotalPositions)).is_greater(0)

# Acceptance anchors:
# ACC:T10.1
func test_token_moves_to_index_position_without_animation() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2(10, 0)
    view.StepPixels = 5.0
    view.MoveDurationSeconds = 0.0

    add_child(auto_free(view))
    await get_tree().process_frame

    _publish_move("p1", 3)
    await get_tree().process_frame

    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(_target_position(view, 3))

func test_token_move_sets_animated_flag_when_duration_positive() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _publish_move("p1", 2)
    await _await_until(func() -> bool: return view.LastMoveAnimated, 30)

    assert_bool(view.LastMoveAnimated).is_true()

# Acceptance anchors:
# ACC:T10.2
func test_token_move_animation_duration_reaches_target_after_expected_time() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    var start_pos: Vector2 = token.position
    var target: Vector2 = _target_position(view, 5)
    var start_ms: int = Time.get_ticks_msec()

    _publish_move("p1", 5)
    assert_vector(token.position).is_equal(start_pos)
    assert_bool(view.LastMoveAnimated).is_true()

    await _await_until(func() -> bool: return token.position.distance_to(start_pos) > 0.01, 60)
    var reached_ms := -1
    for _i in range(240):
        await get_tree().process_frame
        if token.position.distance_to(target) <= 0.5:
            reached_ms = Time.get_ticks_msec()
            break
    assert_int(reached_ms).is_greater(0)
    var elapsed_ms: int = int(reached_ms - start_ms)
    var expected_ms: int = int(view.MoveDurationSeconds * 1000.0)
    var min_ms: int = int(round(float(expected_ms) * 0.5))
    var max_ms: int = int(round(float(expected_ms) * 8.0))
    assert_int(elapsed_ms).is_greater_equal(min_ms)
    assert_int(elapsed_ms).is_less_equal(max_ms)
    assert_float(token.position.x).is_between(target.x - 0.5, target.x + 0.5)
    assert_float(token.position.y).is_between(target.y - 0.5, target.y + 0.5)

# Acceptance anchors:
# ACC:T10.3
func test_token_moves_continuously_last_event_wins() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2(3, 0)
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    var start_pos: Vector2 = token.position
    var target: Vector2 = _target_position(view, 1)

    _publish_move("p1", 8)
    await _await_until(func() -> bool: return token.position.distance_to(start_pos) > 0.01, 60)
    _publish_move("p1", 1)

    await _await_until(func() -> bool: return token.position.distance_to(target) <= 0.5, 240)
    assert_int(view.LastToIndex).is_equal(1)
    assert_float(token.position.x).is_between(target.x - 0.5, target.x + 0.5)

# Acceptance anchors:
# ACC:T10.4
func test_instant_move_overrides_animation_when_duration_is_zero() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _publish_move("p1", 2)
    await get_tree().process_frame

    view.MoveDurationSeconds = 0.0
    _publish_move("p1", 4)

    assert_bool(view.LastMoveAnimated).is_false()
    var target: Vector2 = _target_position(view, 4)
    assert_float(token.position.x).is_between(target.x - 0.5, target.x + 0.5)
    for _i in range(10):
        await get_tree().process_frame
        assert_float(token.position.x).is_between(target.x - 0.5, target.x + 0.5)

func test_ready_without_eventbus_does_not_crash() -> void:
    var original_name: String = _bus.name
    _bus.name = "__EventBusHidden__"

    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    add_child(auto_free(view))
    await get_tree().process_frame

    assert_bool(view.is_inside_tree()).is_true()
    _bus.name = original_name

func test_token_path_missing_ignores_event_and_does_not_crash() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.TokenPath = NodePath("MissingToken")
    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _publish_move("p1", 5)
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

func test_invalid_json_does_not_crash_and_does_not_move_token() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _publish_move("p1", 5, "{invalid_json")
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

# ACC:T10.5
func test_negative_to_index_is_ignored_and_does_not_move_token() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.0

    add_child(auto_free(view))
    await get_tree().process_frame

    var before_lines := _read_security_audit_lines()
    _publish_move("p1", -1)
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

    _assert_last_security_audit_entry_appended(before_lines, "SANGUO_BOARD_TOKEN_MOVE_REJECTED", "to_index_negative")

# Acceptance anchors:
# ACC:T17.6
func test_token_move_is_rejected_when_total_positions_not_configured() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.0
    view.TotalPositions = 0

    add_child(auto_free(view))
    await get_tree().process_frame

    var before_lines := _read_security_audit_lines()
    _publish_move("p1", 1)
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

    _assert_last_security_audit_entry_appended(before_lines, "SANGUO_BOARD_TOKEN_MOVE_REJECTED", "total_positions_not_configured")

# Acceptance anchors:
# ACC:T17.6
func test_dice_roll_publishes_token_move_within_total_positions() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2(10, 0)
    view.StepPixels = 5.0
    view.MoveDurationSeconds = 0.0

    add_child(auto_free(view))
    await get_tree().process_frame

    var total_positions: int = int(view.TotalPositions)
    assert_int(total_positions).is_greater(0)

    _publish_dice("p1", 6)
    await get_tree().process_frame

    var first_to_index: int = int(view.LastToIndex)
    assert_int(first_to_index).is_greater_equal(0)
    assert_int(first_to_index).is_less(total_positions)
    assert_vector(token.position).is_equal(_target_position(view, first_to_index))

    _publish_dice("p1", 6)
    await get_tree().process_frame

    var expected_second: int = int((first_to_index + 6) % total_positions)
    var second_to_index: int = int(view.LastToIndex)
    assert_int(second_to_index).is_equal(expected_second)
    assert_int(second_to_index).is_greater_equal(0)
    assert_int(second_to_index).is_less(total_positions)
    assert_vector(token.position).is_equal(_target_position(view, second_to_index))

# Acceptance anchors:
# ACC:T17.6
func test_dice_roll_does_not_publish_token_move_when_total_positions_not_configured() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.0
    view.TotalPositions = 0

    add_child(auto_free(view))
    await get_tree().process_frame

    var before_lines := _read_security_audit_lines()
    _publish_dice("p1", 6)
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

    var after_lines := _read_security_audit_lines()
    assert_int(after_lines.size()).is_equal(before_lines.size())

# ACC:T10.6
func test_out_of_range_to_index_is_ignored_when_total_positions_set() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")
    var start_pos: Vector2 = token.position

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.0
    view.TotalPositions = 3

    add_child(auto_free(view))
    await get_tree().process_frame

    var before_lines := _read_security_audit_lines()
    _publish_move("p1", 3)
    await get_tree().process_frame

    assert_int(view.LastToIndex).is_equal(0)
    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(start_pos)

    _assert_last_security_audit_entry_appended(before_lines, "SANGUO_BOARD_TOKEN_MOVE_REJECTED", "to_index_out_of_range")
