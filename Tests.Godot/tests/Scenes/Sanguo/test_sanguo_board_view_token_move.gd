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
