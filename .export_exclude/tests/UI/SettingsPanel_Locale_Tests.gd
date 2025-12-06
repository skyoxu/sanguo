extends GdUnitTestSuite

func test_language_applies_runtime() -> void:
    var panel = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn").instantiate()
    add_child(panel)
    var lang_opt = panel.get_node("VBox/LangRow/LangOpt")
    if lang_opt.get_item_count() == 0:
        lang_opt.add_item("en"); lang_opt.add_item("zh")
    lang_opt.select(1)
    # simulate selection
    lang_opt.emit_signal("item_selected", 1)
    await await_idle_frame()
    assert_str(TranslationServer.get_locale()).contains("zh")
    panel.queue_free()
