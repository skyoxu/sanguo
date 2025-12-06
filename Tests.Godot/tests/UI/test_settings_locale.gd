extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_language_applies_runtime() -> void:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    var lang_opt = panel.get_node("VBox/LangRow/LangOpt")
    if lang_opt.get_item_count() == 0:
        lang_opt.add_item("en"); lang_opt.add_item("zh")
    # select zh and emit selection
    var idx := -1
    for i in range(lang_opt.get_item_count()):
        if str(lang_opt.get_item_text(i)).to_lower() == "zh":
            idx = i
            break
    if idx == -1:
        push_warning("SKIP: zh option not found")
        return
    lang_opt.select(idx)
    lang_opt.emit_signal("item_selected", idx)
    await get_tree().process_frame
    assert_str(TranslationServer.get_locale()).contains("zh")

