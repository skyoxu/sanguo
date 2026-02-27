extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

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
    var menu := main.get_node_or_null("MenuLayer/MainMenu")
    if menu == null:
        menu = main.get_node_or_null("MainMenu")
    assert_object(menu).is_not_null()
    var btn = menu.get_node_or_null("MenuRow/MenuBox/BtnPlay")
    if btn == null:
        btn = menu.get_node_or_null("VBox/BtnPlay")
    assert_object(btn).is_not_null()
    btn.emit_signal("pressed")

    var btn_start = menu.get_node_or_null("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart")
    if btn_start == null:
        btn_start = menu.get_node_or_null("ConfigCenter/NewGameConfig/VBox/BtnStart")
    assert_object(btn_start).is_not_null()
    btn_start.emit_signal("pressed")

    await get_tree().process_frame
    assert_bool(_got).is_true()
    assert_bool(_types.has("ui.menu.start")).is_true()
