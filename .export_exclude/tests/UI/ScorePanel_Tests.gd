extends GdUnitTestSuite

var _events := []

func _on_evt(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    _events.append(type)

func test_score_panel_add10_emits_event_or_updates() -> void:
    if not _demo_enabled():
        push_warning("SKIP demo test: set TEMPLATE_DEMO=1 to enable")
        return
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

    var panel = load("res://Game.Godot/Examples/UI/ScorePanel.tscn").instantiate()
    add_child(panel)
    var btn = panel.get_node("VBox/Buttons/Add10")
    btn.emit_signal("pressed")
    await await_idle_frame()
    assert_bool(_events.has("core.score.updated") or _events.has("score.changed")).is_true()
    panel.queue_free()



