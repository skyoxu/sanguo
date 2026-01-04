extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T22.1
# ACC:T9.1
# ACC:T20.1
func test_hud_scene_instantiates() -> void:
    var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    assert_bool(main.is_inside_tree()).is_true()
    assert_bool(main.visible).is_true()

    assert_object(main.theme).is_not_null()
    assert_str(main.theme.resource_path).contains("res://Game.Godot/Themes/default_theme.tres")

    var hud := main.get_node_or_null("HUD")
    assert_object(hud).is_not_null()
    assert_object(hud.get_node_or_null("EventToast")).is_not_null()
    assert_object(hud.get_node_or_null("EventLogPanel")).is_not_null()
    var money_label: Label = hud.get_node("TopBar/HBox/MoneyLabel")
    assert_str(money_label.text).is_equal("Money: -")

    var toast := preload("res://Game.Godot/Scenes/UI/EventToast.tscn").instantiate()
    add_child(auto_free(toast))

    var log_panel := preload("res://Game.Godot/Scenes/UI/EventLogPanel.tscn").instantiate()
    add_child(auto_free(log_panel))
    await get_tree().process_frame

    assert_bool(toast.is_inside_tree()).is_true()
    assert_bool(log_panel.is_inside_tree()).is_true()
