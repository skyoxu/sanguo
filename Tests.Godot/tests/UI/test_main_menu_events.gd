extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _received := false
var _etype := ""

func before() -> void:
    # Install a temporary EventBus under /root to mimic Autoload
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _received = true
    _etype = str(type)

# ACC:T28.2
func test_main_menu_emits_start() -> void:
    _received = false
    var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(auto_free(menu))
    await get_tree().process_frame
    var btn_play = menu.get_node("MenuRow/MenuBox/BtnPlay")
    var btn_start = menu.get_node("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart")
    btn_play.emit_signal("pressed")
    await get_tree().process_frame
    btn_start.emit_signal("pressed")
    for _i in range(60):
        if _received:
            break
        await get_tree().process_frame
    assert_bool(_received).is_true()
    assert_str(_etype).is_equal("ui.menu.start")
