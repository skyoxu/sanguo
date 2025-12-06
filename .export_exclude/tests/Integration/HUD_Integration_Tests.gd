extends GdUnitTestSuite

func _load_main():
    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)
    await await_idle_frame()
    return main

func test_hud_updates_on_core_events() -> void:
    var main = await _load_main()
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()

    # publish score update
    bus.PublishSimple("core.score.updated", "ut", '{"value":123}')
    await await_idle_frame()
    var hud = main.get_node("HUD")
    var score_label = hud.get_node("TopBar/HBox/ScoreLabel")
    assert_str(score_label.text).contains("123")

    # publish health update
    bus.PublishSimple("core.health.updated", "ut", '{"value":77}')
    await await_idle_frame()
    var hp_label = hud.get_node("TopBar/HBox/HealthLabel")
    assert_str(hp_label.text).contains("77")

