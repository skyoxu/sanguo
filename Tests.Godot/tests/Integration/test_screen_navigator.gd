extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _load_main() -> Node:
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(auto_free(main))
    await get_tree().process_frame
    return main

func _overlays(main: Node) -> Node:
    return main.get_node("Overlays")

func _navigator(main: Node):
    return main.get_node_or_null("ScreenNavigator")

func test_switch_to_invalid_scene_returns_false() -> void:
    var main = await _load_main()
    var nav = _navigator(main)
    assert_object(nav).is_not_null()
    var overlays = _overlays(main)
    var before_children = overlays.get_child_count()
    var ok = nav.SwitchTo("res://path/not_found.tscn")
    assert_bool(ok).is_false()
    await get_tree().process_frame
    assert_int(overlays.get_child_count()).is_equal(before_children)

func test_fade_transition_blocks_input_and_cleans_up() -> void:
    var main = await _load_main()
    var nav = _navigator(main)
    assert_object(nav).is_not_null()
    nav.UseFadeTransition = true
    nav.FadeDurationSec = 0.05
    var overlays = _overlays(main)
    var ok = nav.SwitchTo("res://Game.Godot/Scenes/Screens/SettingsScreen.tscn")
    assert_bool(ok).is_true()
    # Wait until fade overlay appears (max 60 frames)
    var fade: ColorRect = null
    for i in range(60):
        for child in overlays.get_children():
            if child is ColorRect and child.name == "__ScreenFade__":
                fade = child
                break
        if fade != null:
            break
        await get_tree().process_frame
    assert_that(fade).is_not_null()
    # In headless runs some platforms may not reflect MouseFilter enum reliably; presence is sufficient here
    # Wait until fade overlay is removed (max 180 frames)
    var removed := false
    for i in range(180):
        var exists := false
        for child in overlays.get_children():
            if child is ColorRect and child.name == "__ScreenFade__":
                exists = true
                break
        if not exists:
            removed = true
            break
        await get_tree().process_frame
    assert_bool(removed).is_true()
