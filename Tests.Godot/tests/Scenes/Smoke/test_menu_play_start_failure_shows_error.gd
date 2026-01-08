extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVT_START := "ui.menu.start"
const EVT_START_FAILED := "ui.menu.start.failed"

var _bus: Node
var _types: Array = []

func before() -> void:
    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))
    _types = []

    # Force game start failure by injecting a failing loader into the expected port path.
    var existing_root = get_node_or_null("/root/CompositionRoot")
    if existing_root != null:
        existing_root.name = "CompositionRoot__old__%s" % str(Time.get_ticks_msec())
        existing_root.queue_free()

    var cr = Node.new()
    cr.name = "CompositionRoot"
    get_tree().get_root().add_child(auto_free(cr))

    var loader = preload("res://Game.Godot/Adapters/TestFailingResourceLoader.cs").new()
    loader.name = "ResourceLoaderPort"
    cr.add_child(auto_free(loader))

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _types.append(str(type))

# ACC:T28.9
func test_play_start_failure_keeps_menu_visible_and_shows_error() -> void:
    _types.clear()
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame

    var menu := main.get_node_or_null("MainMenu")
    assert_object(menu).is_not_null()
    if menu == null:
        return

    var btn_play = menu.get_node("VBox/BtnPlay")
    btn_play.emit_signal("pressed")

    for _i in range(120):
        if _types.has(EVT_START_FAILED):
            break
        await get_tree().process_frame

    assert_bool(_types.has(EVT_START)).is_true()
    assert_bool(_types.has(EVT_START_FAILED)).is_true()
    assert_bool(menu.visible).is_true()

    var status = menu.get_node_or_null("StatusLabel")
    assert_object(status).is_not_null()
    if status != null:
        assert_bool((status as Label).visible).is_true()
        assert_str((status as Label).text).contains("Start failed")

    assert_bool((btn_play as Button).disabled).is_false()

