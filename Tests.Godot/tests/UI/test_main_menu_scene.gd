extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T28.1
func test_main_menu_scene_instantiates() -> void:
    var scene := preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.visible).is_true()
