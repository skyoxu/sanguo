extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Validate primary buttons can be invoked via signals (no InputEvents in headless)

var _save_called := false

func _instantiate_settings_panel() -> Node:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return null
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    return panel

func _on_save_pressed() -> void:
    _save_called = true

func test_buttons_emit_pressed_and_panel_hides_on_close() -> void:
    var panel = await _instantiate_settings_panel()
    if panel == null:
        return
    # Ensure visible then close
    if panel.has_method("ShowPanel"):
        panel.ShowPanel()
    await get_tree().process_frame
    assert_bool(panel.visible).is_true()
    var save_btn: Button = panel.get_node("Center/VBox/Buttons/SaveBtn")
    var close_btn: Button = panel.get_node("Center/VBox/Buttons/CloseBtn")
    _save_called = false
    save_btn.connect("pressed", Callable(self, "_on_save_pressed"), CONNECT_ONE_SHOT)
    save_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(_save_called).is_true()
    close_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(panel.visible).is_false()
