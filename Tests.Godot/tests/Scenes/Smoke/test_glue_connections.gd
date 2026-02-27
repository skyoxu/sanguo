extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

var _bus: Node
var _etype := ""
var _got := false
var _types: Array = []

func before() -> void:
    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))
    _types = []

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _etype = str(type)
    _got = true
    _types.append(str(type))

func test_main_scene_glue_publishes_on_menu_start() -> void:
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    var menu := MenuTestDriver.resolve_menu(main)
    assert_object(menu).is_not_null()
    var ok := MenuTestDriver.press_play_then_start(menu)
    assert_bool(ok).is_true()

    await get_tree().process_frame
    assert_bool(_got).is_true()
    assert_bool(_types.has("ui.menu.start")).is_true()
