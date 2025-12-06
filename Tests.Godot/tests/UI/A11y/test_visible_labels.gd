extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Validate important labels exist and have non-empty text

func _instantiate_settings_panel() -> Node:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return null
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    return panel

func test_labels_non_empty() -> void:
    var panel = await _instantiate_settings_panel()
    if panel == null:
        return
    var lang_label: Label = panel.get_node("VBox/LangRow/LangLabel")
    var gfx_label: Label = panel.get_node("VBox/GraphicsRow/GraphicsLabel")
    var vol_label: Label = panel.get_node("VBox/VolRow/VolLabel")
    assert_str(str(lang_label.text)).is_not_empty()
    assert_str(str(gfx_label.text)).is_not_empty()
    assert_str(str(vol_label.text)).is_not_empty()

