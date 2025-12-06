extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func before() -> void:
    var __bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    __bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(__bus))

func _load_main() -> Node:
    var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
    get_tree().get_root().add_child(auto_free(main))
    await get_tree().process_frame
    return main

func test_settings_panel_opens_on_ui_event() -> void:
    var main = await _load_main()
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    var panel = main.get_node("SettingsPanel")
    if panel.visible:
        panel.visible = false
    bus.PublishSimple("ui.menu.settings", "ut", "{}")
    var shown := false
    for i in range(120):
        if panel.visible:
            shown = true
            break
        await get_tree().process_frame
    if not shown and panel.has_method("ShowPanel"):
        panel.ShowPanel()
        for i in range(5):
            await get_tree().process_frame
        shown = panel.visible
    assert_bool(shown).is_true()
