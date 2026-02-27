extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T28.1
func test_main_menu_scene_instantiates() -> void:
    var scene := preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(auto_free(scene))
    await get_tree().process_frame
    assert_bool(scene.visible).is_true()

    var btn_play = scene.get_node_or_null("MenuRow/MenuBox/BtnPlay")
    var btn_load = scene.get_node_or_null("MenuRow/MenuBox/BtnLoad")
    var btn_quit = scene.get_node_or_null("MenuRow/MenuBox/BtnQuit")
    assert_object(btn_play).is_not_null()
    assert_object(btn_load).is_not_null()
    assert_object(btn_quit).is_not_null()
    if btn_play != null:
        assert_bool((btn_play as Button).disabled).is_false()
    if btn_load != null:
        assert_bool((btn_load as Button).disabled).is_false()
    if btn_quit != null:
        assert_bool((btn_quit as Button).disabled).is_false()
