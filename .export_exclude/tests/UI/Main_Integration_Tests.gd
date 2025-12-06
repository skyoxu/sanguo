extends GdUnitTestSuite

var _events := []

func _on_evt(type: String, source: String, data_json: String, id: String, spec: String, ct: String, ts: String) -> void:
    _events.append(type)

func test_play_starts_engine_and_emits_event() -> void:
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)

    var menu = main.get_node("MainMenu")
    var btn_play = menu.get_node("VBox/BtnPlay")
    btn_play.emit_signal("pressed")
    await await_idle_frame()

    # Expect 'game.started' to be emitted by GameEngineDemo.StartGame()
    assert_bool(_events.has("game.started")).is_true()
    main.queue_free()

