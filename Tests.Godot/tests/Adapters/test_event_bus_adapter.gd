extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _emitted := false

func before() -> void:
    _bus = load("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"), CONNECT_ONE_SHOT)

func _on_evt(_type, _source, _data_json, _id, _spec, _ct, _ts):
    _emitted = true

func test_publish_simple_emits_signal() -> void:
    _emitted = false
    _bus.PublishSimple("test.evt", "gdunit", "{}")
    await get_tree().process_frame
    assert_bool(_emitted).is_true()

