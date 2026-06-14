extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

var _evt_got := false
var _evt_type := ""
var _evt_types: Array = []

func _on_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _evt_got = true
    _evt_type = str(type)
    _evt_types.append(str(type))

# ACC:T1.1
# ACC:T184.7
func test_main_scene_instantiates_and_visible() -> void:
    var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.is_inside_tree()).is_true()
    assert_bool(scene.visible).is_true()

# ACC:T206.1
# ACC:T206.3
# ACC:T206.4
# ACC:T215.1
func test_main_scene_exposes_core_playable_recovery_surfaces() -> void:
    var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame

    assert_object(scene.get_node_or_null("MenuLayer/MainMenu")).is_not_null()
    var menu := MenuTestDriver.resolve_menu(scene)
    assert_object(menu).is_not_null()
    if menu != null:
        assert_object(MenuTestDriver.resolve_play_button(menu)).is_not_null()
        assert_object(MenuTestDriver.resolve_load_button(menu)).is_not_null()
        assert_object(MenuTestDriver.resolve_start_button(menu)).is_not_null()
        assert_object(MenuTestDriver.resolve_status_label(menu)).is_not_null()
    var hud = scene.get_node_or_null("SplitRoot/TopArea/HudLayer/HUD")
    assert_object(hud).is_not_null()
    if hud != null:
        assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/ActivePlayerLabel")).is_not_null()
        assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/DateLabel")).is_not_null()
        assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/MoneyLabel")).is_not_null()
        assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/HealthLabel")).is_not_null()
        assert_object(hud.get_node_or_null("EventResultPopup/Center/Panel/VBox/Message")).is_not_null()
        assert_object(hud.get_node_or_null("ActionPanel/VBox/ActionTitle")).is_not_null()
    assert_object(scene.get_node_or_null("SplitRoot/BottomArea/BoardArea/BoardViewportContainer/BoardViewport/SanguoBoardView")).is_not_null()
    assert_object(scene.get_node_or_null("SplitRoot/BottomArea/BoardArea/Overlays/SanguoBattleView")).is_not_null()
    var settlement = scene.get_node_or_null("SplitRoot/BottomArea/BoardArea/Overlays/SettlementScreen")
    assert_object(settlement).is_not_null()
    if settlement != null:
        assert_object(settlement.get_node_or_null("Center/Panel/VBox/Title")).is_not_null()
        assert_object(settlement.get_node_or_null("Center/Panel/VBox/WinnerLabel")).is_not_null()
        assert_object(settlement.get_node_or_null("Center/Panel/VBox/StatsSnapshotLabel")).is_not_null()
        assert_object(settlement.get_node_or_null("Center/Panel/VBox/Buttons/NewGameButton")).is_not_null()

    var output := scene.get_node_or_null("SplitRoot/TopArea/VBox/Output")
    assert_object(output).is_not_null()
    if output != null:
        assert_str(str(output.text)).is_equal("Ready")

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
