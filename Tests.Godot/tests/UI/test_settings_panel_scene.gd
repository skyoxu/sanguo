extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T29.1
func test_settings_panel_scene_instantiates() -> void:
    var scene := preload("res://Game.Godot/Scenes/UI/SettingsPanel.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.is_inside_tree()).is_true()
