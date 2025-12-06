extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_panel_close_button_hides_panel() -> void:
    var panel = preload("res://Game.Godot/Scenes/UI/SettingsPanel.tscn").instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    # Ensure visible first
    if not panel.visible:
        panel.visible = true
        await get_tree().process_frame
    assert_bool(panel.visible).is_true()
    # White-box: click CloseBtn and expect hidden
    var close_btn = panel.get_node("VBox/Buttons/CloseBtn")
    close_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(panel.visible).is_false()

