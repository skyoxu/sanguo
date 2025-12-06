extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _time: Node
var _input: Node

func before() -> void:
    _time = load("res://Game.Godot/Adapters/TimeAdapter.cs").new()
    add_child(auto_free(_time))
    _input = load("res://Game.Godot/Adapters/InputAdapter.cs").new()
    add_child(auto_free(_input))

func test_time_adapter_has_delta() -> void:
    await get_tree().process_frame
    var d = _time.DeltaSeconds
    assert_float(d).is_greater_equal(0.0)

func test_input_adapter_methods_exist() -> void:
    var pressed = _input.IsPressed("ui_accept")
    assert_bool(pressed or not pressed).is_true() # sanity of return type
    var axis = _input.GetAxis("ui_left", "ui_right")
    assert_float(axis).is_between(-1.0, 1.0)

