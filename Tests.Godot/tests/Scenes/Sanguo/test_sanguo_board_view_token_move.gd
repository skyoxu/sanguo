extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node

func before() -> void:
    _bus = load("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func test_token_moves_to_index_position_without_animation() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2(10, 0)
    view.StepPixels = 5.0
    view.MoveDurationSeconds = 0.0

    add_child(auto_free(view))
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":3}")
    await get_tree().process_frame

    assert_bool(view.LastMoveAnimated).is_false()
    assert_vector(token.position).is_equal(Vector2(25, 0))

func test_token_move_sets_animated_flag_when_duration_positive() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":2}")
    await get_tree().process_frame

    assert_bool(view.LastMoveAnimated).is_true()

func test_token_move_animation_duration_reaches_target_after_expected_time() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":5}")
    await get_tree().create_timer(0.05).timeout
    assert_bool(token.position.x < 50.0).is_true()

    await get_tree().create_timer(0.25).timeout
    assert_float(token.position.x).is_between(49.9, 50.1)
    assert_float(token.position.y).is_between(-0.1, 0.1)

func test_token_moves_continuously_last_event_wins() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2(3, 0)
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":8}")
    await get_tree().create_timer(0.05).timeout
    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":1}")

    await get_tree().create_timer(0.30).timeout
    assert_int(view.LastToIndex).is_equal(1)
    assert_float(token.position.x).is_between(12.9, 13.1)

func test_instant_move_overrides_animation_when_duration_is_zero() -> void:
    var view = load("res://Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn").instantiate()
    var token = view.get_node("Token")

    view.Origin = Vector2.ZERO
    view.StepPixels = 10.0
    view.MoveDurationSeconds = 0.2

    add_child(auto_free(view))
    await get_tree().process_frame

    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":2}")
    await get_tree().create_timer(0.05).timeout

    view.MoveDurationSeconds = 0.0
    _bus.PublishSimple("core.sanguo.board.token.moved", "gdunit", "{\"PlayerId\":\"p1\",\"ToIndex\":4}")
    await get_tree().process_frame

    assert_bool(view.LastMoveAnimated).is_false()
    assert_float(token.position.x).is_between(39.9, 40.1)
