extends GdUnitTestSuite

func _load_main():
    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)
    await await_idle_frame()
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
    var before_children := overlays.get_child_count()
    var ok := nav.SwitchTo("res://path/not_found.tscn")
    assert_bool(ok).is_false()
    await await_idle_frame()
    # no fade node created, overlays child count unchanged
    assert_int(overlays.get_child_count()).is_equal(before_children)

func test_fade_transition_blocks_input_and_cleans_up() -> void:
    var main = await _load_main()
    var nav = _navigator(main)
    assert_object(nav).is_not_null()
    # enable fade and shorten duration
    nav.UseFadeTransition = true
    nav.FadeDurationSec = 0.05
    var overlays = _overlays(main)
    var ok := nav.SwitchTo("res://Game.Godot/Scenes/Screens/SettingsScreen.tscn")
    assert_bool(ok).is_true()
    await await_idle_frame()
    # during fade, there should be a ColorRect masking input
    var has_fade := false
    for child in overlays.get_children():
        if child is ColorRect and child.name == "__ScreenFade__":
            has_fade = true
            # MouseFilter.Stop == 2
            assert_int(int(child.mouse_filter)).is_equal(2)
    assert_bool(has_fade).is_true()
    # wait a few frames for fade-out and cleanup
    for i in 10:
        await await_idle_frame()
    # no fade node remains
    var still_fade := false
    for child in overlays.get_children():
        if child is ColorRect and child.name == "__ScreenFade__":
            still_fade = true
    assert_bool(still_fade).is_false()

