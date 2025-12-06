extends GdUnitTestSuite

var _received := false
var _type := ""

func _on_evt(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    _received = true
    _type = type

func test_main_menu_emits_start() -> void:
    var menu = load("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(menu)
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))
    var btn = menu.get_node("VBox/BtnPlay")
    btn.emit_signal("pressed")
    await await_idle_frame()
    assert_bool(_received).is_true()
    assert_str(_type).is_equal("ui.menu.start")
    menu.queue_free()
