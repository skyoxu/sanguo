extends GdUnitTestSuite

func test_signal_scope_connects_and_cleans() -> void:
    if not _demo_enabled():
        push_warning("SKIP demo test: set TEMPLATE_DEMO=1 to enable")
        return
    var panel = load("res://Game.Godot/Examples/Components/EventListenerPanel.tscn").instantiate()
    add_child(panel)
    # connect via Enter lifecycle
    if panel.has_method("Enter"):
        panel.Enter()
    # publish an event
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.PublishSimple("screen.demo.ping", "ut", "{}")
    await await_idle_frame()
    # count should be 1
    var cnt_label = panel.get_node("VBox/Count")
    assert_str(cnt_label.text).is_equal("1")
    # free and publish again; should not error
    panel.queue_free()
    await await_idle_frame()
    bus.PublishSimple("screen.demo.ping", "ut", "{}")
    await await_idle_frame()
