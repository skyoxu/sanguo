extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _events := []

func before() -> void:
    var __bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    __bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(__bus))

func _on_evt(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    _events.append(type)

func test_score_panel_add10_emits_event_or_updates() -> void:
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

    var packed = load("res://Game.Godot/Examples/UI/ScorePanel.tscn")
    if packed == null:
        push_warning("SKIP score_panel test: ScorePanel.tscn not found")
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    var btn = panel.get_node("VBox/Buttons/Add10")
    btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(_events.has("core.score.updated") or _events.has("score.changed")).is_true()
    panel.queue_free()
