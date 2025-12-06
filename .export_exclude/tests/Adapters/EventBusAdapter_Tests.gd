extends GdUnitTestSuite

var _received := false

func _on_evt(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    if type == "test.event" and source == "ut":
        _received = true

func test_event_bus_signal() -> void:
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))
    bus.PublishSimple("test.event", "ut", "{\"a\":1}")
    await await_idle_frame()
    assert_bool(_received).is_true()

