extends GdUnitTestSuite

func _load_main():
    var main = load("res://Game.Godot/Scenes/Main.tscn").instantiate()
    add_child(main)
    await await_idle_frame()
    return main

func test_settings_panel_opens_on_ui_event() -> void:
    var main = await _load_main()
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    var panel = main.get_node("SettingsPanel")
    # ensure starts hidden
    if panel.visible:
        panel.visible = false
    bus.PublishSimple("ui.menu.settings", "ut", "{}")
    await await_idle_frame()
    assert_bool(panel.visible).is_true()

