extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T22.1
# ACC:T9.1
func test_hud_scene_instantiates() -> void:
    var scene := preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.visible).is_true()
