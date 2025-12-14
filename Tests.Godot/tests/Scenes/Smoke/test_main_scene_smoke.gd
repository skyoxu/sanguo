extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_main_scene_instantiates_and_visible() -> void:
    var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.visible).is_true()

func test_settings_screen_can_load() -> void:
    var packed : PackedScene = preload("res://Game.Godot/Scenes/Screens/SettingsScreen.tscn")
    var inst := packed.instantiate()
    add_child(auto_free(inst))
    await get_tree().process_frame
    assert_bool(inst.is_inside_tree()).is_true()
