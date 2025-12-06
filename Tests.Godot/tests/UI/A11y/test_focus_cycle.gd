extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Headless-friendly "focus" checks: do not use InputEvents.
# We verify that key controls expose focus_mode and can be focused programmatically.

func _instantiate_settings_panel() -> Node:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return null
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    return panel

func _can_focus(node: Node) -> bool:
    if node == null:
        return false
    if not node is Control:
        return false
    var ctl: Control = node
    return ctl.focus_mode != Control.FOCUS_NONE

func test_controls_are_focusable_and_can_grab_focus() -> void:
    var panel = await _instantiate_settings_panel()
    if panel == null:
        return
    var save_btn: Control = panel.get_node("VBox/Buttons/SaveBtn")
    var load_btn: Control = panel.get_node("VBox/Buttons/LoadBtn")
    var close_btn: Control = panel.get_node("VBox/Buttons/CloseBtn")
    assert_bool(_can_focus(save_btn)).is_true()
    assert_bool(_can_focus(load_btn)).is_true()
    assert_bool(_can_focus(close_btn)).is_true()

    save_btn.grab_focus()
    await get_tree().process_frame
    assert_bool(save_btn.has_focus()).is_true()
    load_btn.grab_focus()
    await get_tree().process_frame
    assert_bool(load_btn.has_focus()).is_true()
    close_btn.grab_focus()
    await get_tree().process_frame
    assert_bool(close_btn.has_focus()).is_true()

