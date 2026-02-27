extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVT_QUIT := "ui.menu.quit"

var _bus: Node
var _quit_requested := false
var _types: Array = []

func before() -> void:
    OS.set_environment("GD_DISABLE_QUIT", "1")

    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))
    _types = []
    _quit_requested = false

func after() -> void:
    OS.set_environment("GD_DISABLE_QUIT", "0")

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _types.append(str(type))

func _on_quit_requested() -> void:
    _quit_requested = true

func _read_res_text(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var f = FileAccess.open(path, FileAccess.READ)
    if f == null:
        return ""
    return f.get_as_text(true)

# ACC:T28.7
func test_menu_quit_event_is_consumed_by_game_loop_controller() -> void:
    var controller = preload("res://Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs").new()
    add_child(auto_free(controller))
    await get_tree().process_frame
    controller.connect("QuitRequested", Callable(self, "_on_quit_requested"))

    var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(auto_free(menu))
    await get_tree().process_frame

    var btn_quit = menu.get_node_or_null("MenuRow/MenuBox/BtnQuit")
    if btn_quit == null:
        btn_quit = menu.get_node_or_null("VBox/BtnQuit")
    assert_object(btn_quit).is_not_null()
    if btn_quit == null:
        return
    btn_quit.emit_signal("pressed")

    for _i in range(30):
        if _quit_requested:
            break
        await get_tree().process_frame

    assert_bool(_types.has(EVT_QUIT)).is_true()
    assert_bool(_quit_requested).is_true()

    var src = _read_res_text("res://Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs")
    assert_str(src).contains("GD_DISABLE_QUIT")
    assert_str(src).contains("GetTree().Quit")
