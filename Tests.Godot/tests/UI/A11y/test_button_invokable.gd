extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Validate primary buttons can be invoked via signals (no InputEvents in headless)

func _instantiate_settings_panel() -> Node:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return null
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    return panel

func test_buttons_emit_pressed_and_panel_hides_on_close() -> void:
    var panel = await _instantiate_settings_panel()
    if panel == null:
        return
    # Ensure visible then close
    if panel.has_method("ShowPanel"):
        panel.ShowPanel()
    await get_tree().process_frame
    assert_bool(panel.visible).is_true()
    var save_btn = panel.get_node("VBox/Buttons/SaveBtn")
    var load_btn = panel.get_node("VBox/Buttons/LoadBtn")
    var close_btn = panel.get_node("VBox/Buttons/CloseBtn")
    var save_called := false
    var load_called := false
    save_btn.pressed.connect(func(): save_called = true)
    load_btn.pressed.connect(func(): load_called = true)
    save_btn.emit_signal("pressed")
    load_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(save_called).is_true()
    assert_bool(load_called).is_true()
    close_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(panel.visible).is_false()

