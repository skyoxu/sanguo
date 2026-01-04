extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _evt_got := false
var _evt_type := ""

func _on_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _evt_got = true
    _evt_type = str(type)

# ACC:T1.1
func test_main_scene_instantiates_and_visible() -> void:
    var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.is_inside_tree()).is_true()
    assert_bool(scene.visible).is_true()

# ACC:T1.2
func test_can_instantiate_csharp_scriptclass() -> void:
    var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    bus.name = "EventBus"
    add_child(auto_free(bus))

    _evt_got = false
    _evt_type = ""
    bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event"))

    await get_tree().process_frame
    assert_bool(bus.is_inside_tree()).is_true()
    assert_bool(bus.has_method("PublishSimple")).is_true()
    bus.call("PublishSimple", "test.csharp.signal", "tests", "{}")
    for _i in range(0, 30):
        if _evt_got:
            break
        await get_tree().process_frame
    assert_bool(_evt_got).is_true()
    assert_str(_evt_type).is_equal("test.csharp.signal")
