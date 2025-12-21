extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TOKEN_MOVED := "core.sanguo.board.token.moved"

var _bus: Node

func before() -> void:
    _bus = load("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func _publish_move(player_id: String, to_index: int, data_json: String = "") -> void:
    var payload := data_json
    if payload.is_empty():
        payload = "{\"PlayerId\":\"%s\",\"ToIndex\":%d}" % [player_id, to_index]
    _bus.PublishSimple(EVENT_TOKEN_MOVED, "gdunit", payload)

func _target_position(view: Node, to_index: int) -> Vector2:
    return view.Origin + Vector2(float(to_index) * float(view.StepPixels), 0.0)

func _await_until(predicate: Callable, max_frames: int = 240) -> void:
    for _i in range(max_frames):
        if predicate.call():
            return
        await get_tree().process_frame
    assert_bool(predicate.call()).is_true()

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

    _publish_move("p1", 5)
    assert_vector(token.position).is_equal(start_pos)
    assert_bool(view.LastMoveAnimated).is_true()

    await _await_until(func() -> bool: return token.position.distance_to(start_pos) > 0.01, 60)
    await _await_until(func() -> bool: return token.position.distance_to(target) <= 0.5, 240)
    assert_float(token.position.x).is_between(target.x - 0.5, target.x + 0.5)
    assert_float(token.position.y).is_between(target.y - 0.5, target.y + 0.5)

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
