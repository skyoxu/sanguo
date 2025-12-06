extends GdUnitTestSuite

func _load_main():
    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)
    await await_idle_frame()
    return main

func test_navigate_start_to_settings_and_back() -> void:
    var main = await _load_main()
    var nav = main.get_node_or_null("ScreenNavigator")
    assert_object(nav).is_not_null()

    # to Settings
    var ok := nav.SwitchTo("res://Game.Godot/Scenes/Screens/SettingsScreen.tscn")
    assert_bool(ok).is_true()
    await await_idle_frame()
    var root = main.get_node("ScreenRoot")
    assert_object(root.get_child(0)).is_not_null()

    # back to Start
    ok = nav.SwitchTo("res://Game.Godot/Scenes/Screens/StartScreen.tscn")
    assert_bool(ok).is_true()
    await await_idle_frame()
    assert_object(root.get_child(0)).is_not_null()
