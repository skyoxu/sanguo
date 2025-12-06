extends GdUnitTestSuite

func _load_main():
    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)
    await await_idle_frame()
    return main

func test_mainmenu_play_navigates_to_screen() -> void:
    var main = await _load_main()
    var root = main.get_node("ScreenRoot")
    var btn_play = main.get_node("MainMenu/VBox/BtnPlay")
    btn_play.emit_signal("pressed")
    await await_idle_frame()
    # Should load either StartScreen (default) or DemoScreen (if TEMPLATE_DEMO=1)
    assert_int(root.get_child_count()).is_greater(0)
    var name := root.get_child(0).name
    assert_bool(name == "StartScreen" or name == "DemoScreen").is_true()

