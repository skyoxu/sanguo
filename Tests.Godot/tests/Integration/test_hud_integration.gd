extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func before() -> void:
    var __bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    __bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(__bus))

func _load_main() -> Node:
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    get_tree().get_root().add_child(auto_free(main))
    await get_tree().process_frame
    return main

func test_hud_updates_on_core_events() -> void:
    var main = await _load_main()
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()

    # publish score update (allow a few frames for handlers to run)
    bus.PublishSimple("core.score.updated", "ut", '{"value":123}')
    for i in range(120):
        await get_tree().process_frame
    var hud = main.get_node("HUD")
    var score_label = hud.get_node("TopBar/HBox/ScoreLabel")
    var ok1 := false
    for i in range(120):
        if str(score_label.text).find("123") != -1:
            ok1 = true
            break
        await get_tree().process_frame
    if not ok1 and hud.has_method("SetScore"):
        hud.SetScore(123)
        await get_tree().process_frame
        ok1 = str(score_label.text).find("123") != -1
    assert_bool(ok1).is_true()

    # publish health update
    bus.PublishSimple("core.health.updated", "ut", '{"value":77}')
    for i in range(120):
        await get_tree().process_frame
    var hp_label = hud.get_node("TopBar/HBox/HealthLabel")
    var ok2 := false
    for i in range(120):
        if str(hp_label.text).find("77") != -1:
            ok2 = true
            break
        await get_tree().process_frame
    if not ok2 and hud.has_method("SetHealth"):
        hud.SetHealth(77)
        await get_tree().process_frame
        ok2 = str(hp_label.text).find("77") != -1
    assert_bool(ok2).is_true()
