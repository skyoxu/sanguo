extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_panel_showpanel_whitebox() -> void:
    var panel = preload("res://Game.Godot/Scenes/UI/SettingsPanel.tscn").instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    if panel.visible:
        panel.visible = false
        await get_tree().process_frame
    assert_bool(panel.visible).is_false()
    if panel.has_method("ShowPanel"):
        panel.ShowPanel()
    await get_tree().process_frame
    assert_bool(panel.visible).is_true()

