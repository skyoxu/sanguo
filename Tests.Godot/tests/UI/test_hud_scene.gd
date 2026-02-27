extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _original_locale := ""

func _assert_label_value(text: String, expected_value: String) -> void:
    assert_bool(text.ends_with(": " + expected_value)).is_true()

func before() -> void:
    if TranslationServer.has_method("get_locale"):
        _original_locale = String(TranslationServer.get_locale())
    if TranslationServer.has_method("set_locale"):
        TranslationServer.set_locale("en")

    var existing = get_node_or_null("/root/EventBus")
    if existing != null:
        existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
        existing.queue_free()

    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))

func after() -> void:
    if TranslationServer.has_method("set_locale") and _original_locale.strip_edges().length() > 0:
        TranslationServer.set_locale(_original_locale)

# ACC:T22.1
# ACC:T9.1
# ACC:T20.1
# ACC:T19.1
# ACC:T21.1
# ACC:T21.4
# ACC:T24.1
func test_hud_scene_instantiates() -> void:
    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    assert_bool(main.is_inside_tree()).is_true()
    assert_bool(main.visible).is_true()

    assert_object(main.theme).is_not_null()
    assert_str(main.theme.resource_path).contains("res://Game.Godot/Themes/default_theme.tres")

    var hud := main.get_node_or_null("SplitRoot/TopArea/HudLayer/HUD")
    assert_object(hud).is_not_null()
    assert_object(hud.get_node_or_null("EventToast")).is_not_null()
    assert_object(hud.get_node_or_null("EventLogPanel")).is_not_null()
    var event_log_panel: Control = hud.get_node("EventLogPanel")
    assert_bool(event_log_panel.visible).is_false()
    hud.call("ToggleEventLogOverlay")
    await get_tree().process_frame
    assert_bool(event_log_panel.visible).is_true()
    var date_label: Label = hud.get_node("TopBar/TopStack/HBox/DateLabel")
    assert_bool(date_label.visible).is_true()
    var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
    _assert_label_value(money_label.text, "-")

    assert_object(main.get_node_or_null("SplitRoot/BottomArea/BoardArea/BoardViewportContainer/BoardViewport/SanguoBoardView")).is_not_null()
    assert_object(main.get_node_or_null("SplitRoot/BottomArea/BoardArea/Overlays/CityOwnershipStatus")).is_not_null()

    _bus.PublishSimple("ui.menu.start", "ut", "{}")
    for _i in range(20):
        await get_tree().process_frame
        if not date_label.text.ends_with(": -"):
            break
    _assert_label_value(date_label.text, "0003-02-01")

    var toast := preload("res://Game.Godot/Scenes/UI/EventToast.tscn").instantiate()
    add_child(auto_free(toast))

    var log_panel := preload("res://Game.Godot/Scenes/UI/EventLogPanel.tscn").instantiate()
    add_child(auto_free(log_panel))
    await get_tree().process_frame

    assert_bool(toast.is_inside_tree()).is_true()
    assert_bool(log_panel.is_inside_tree()).is_true()
    assert_bool(log_panel.is_visible_in_tree()).is_true()
    assert_object(toast.get_node_or_null("Panel/Label")).is_not_null()
    assert_bool(toast.visible).is_false()
    var toast_label: Label = toast.get_node("Panel/Label")
    assert_str(toast_label.text).is_equal("")

func test_event_log_panel_is_bottom_docked() -> void:
    var hud := preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(hud))
    await get_tree().process_frame

    var log_panel: Control = hud.get_node("EventLogPanel")
    assert_float(float(log_panel.anchor_top)).is_equal(1.0)
    assert_float(float(log_panel.anchor_bottom)).is_equal(1.0)
    assert_bool(log_panel.offset_top < 0.0).is_true()
