extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node

func before() -> void:
    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func _hud() -> Node:
    var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(hud))
    await get_tree().process_frame
    return hud

func test_hud_updates_on_score_event() -> void:
    var hud = await _hud()
    var score_label: Label = hud.get_node("TopBar/HBox/ScoreLabel")
    _bus.PublishSimple("core.score.updated", "ut", "{\"value\":42}")
    await get_tree().process_frame
    assert_str(score_label.text).contains("42")

func test_hud_updates_on_health_event() -> void:
    var hud = await _hud()
    var hp_label: Label = hud.get_node("TopBar/HBox/HealthLabel")
    _bus.PublishSimple("core.health.updated", "ut", "{\"value\":77}")
    await get_tree().process_frame
    assert_str(hp_label.text).contains("77")

