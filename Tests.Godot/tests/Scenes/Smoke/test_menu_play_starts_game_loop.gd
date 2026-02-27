extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

const EVT_MENU_START := "ui.menu.start"
const EVT_TURN_STARTED := "core.sanguo.game.turn.started"

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

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _types.append(str(type))

# ACC:T28.8
func test_play_is_consumed_and_turn_started_is_published() -> void:
    _types.clear()
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame

    var menu := MenuTestDriver.resolve_menu(main)
    assert_object(menu).is_not_null()
    if menu == null:
        return

    var ok := MenuTestDriver.press_play_then_start(menu)
    assert_bool(ok).is_true()
    if not ok:
        return

    for _i in range(240):
        if _types.has(EVT_TURN_STARTED):
            break
        await get_tree().process_frame

    assert_bool(_types.has(EVT_MENU_START)).is_true()
    assert_bool(_types.has(EVT_TURN_STARTED)).is_true()
    assert_bool(menu.visible).is_false()

