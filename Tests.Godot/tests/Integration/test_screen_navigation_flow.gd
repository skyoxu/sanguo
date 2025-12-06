extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _load_main() -> Node:
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    return main

func test_navigate_start_to_settings_and_back() -> void:
    var main = await _load_main()
    var nav = main.get_node_or_null("ScreenNavigator")
    assert_object(nav).is_not_null()

    # Disable fade to make switch deterministic in tests
    nav.UseFadeTransition = false
    var ok = nav.SwitchTo("res://Game.Godot/Scenes/Screens/SettingsScreen.tscn")
    assert_bool(ok).is_true()
    await get_tree().process_frame
    var root = main.get_node("ScreenRoot")
    var current = root.get_child(0)
    assert_object(current).is_not_null()
    assert_str(current.name).is_equal("SettingsScreen")

    ok = nav.SwitchTo("res://Game.Godot/Scenes/Screens/StartScreen.tscn")
    assert_bool(ok).is_true()
    await get_tree().process_frame
    current = root.get_child(0)
    assert_object(current).is_not_null()
    assert_str(current.name).is_equal("StartScreen")
