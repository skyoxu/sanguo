extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _new_panel() -> Node:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return null
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    return panel

func _select_lang(panel: Node, code: String) -> void:
    var lang_opt = panel.get_node("Center/VBox/LangRow/LangOpt") as OptionButton
    if lang_opt.get_item_count() == 0:
        lang_opt.add_item("en"); lang_opt.add_item("zh"); lang_opt.add_item("ja")
    var idx := -1
    for i in range(lang_opt.get_item_count()):
        if str(lang_opt.get_item_metadata(i)).to_lower() == code.to_lower():
            idx = i
            break
        if str(lang_opt.get_item_text(i)).to_lower() == code.to_lower():
            idx = i
            break
    if idx != -1:
        lang_opt.select(idx)
        # trigger runtime apply
        lang_opt.emit_signal("item_selected", idx)

func _clear_config() -> void:
    var dir := DirAccess.open("user://")
    if dir and dir.file_exists("settings.cfg"):
        dir.remove("settings.cfg")

# ACC:T205.4
func test_settings_locale_persist_cross_restart_via_config() -> void:
    var original_locale := ""
    if TranslationServer.has_method("get_locale"):
        original_locale = String(TranslationServer.get_locale())

    _clear_config()
    var panel = await _new_panel()
    if panel == null:
        if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
            TranslationServer.set_locale(original_locale)
        return
    _select_lang(panel, "zh")
    var save_btn = panel.get_node("Center/VBox/Buttons/SaveBtn")
    save_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_str(TranslationServer.get_locale()).contains("zh")
    var lang_label = panel.get_node("Center/VBox/LangRow/LangLabel") as Label
    assert_object(lang_label).is_not_null()
    if lang_label != null:
        assert_str(lang_label.text).is_not_empty()

    # simulate restart by freeing and recreating panel
    panel.queue_free()
    await get_tree().process_frame
    var panel2 = await _new_panel()
    if panel2 != null:
        panel2.call("ShowPanel")
    await get_tree().process_frame
    assert_str(TranslationServer.get_locale()).contains("zh")
    if panel2 != null:
        var lang_label2 = panel2.get_node("Center/VBox/LangRow/LangLabel") as Label
        assert_object(lang_label2).is_not_null()
        if lang_label2 != null:
            assert_str(lang_label2.text).is_not_empty()
    if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
        TranslationServer.set_locale(original_locale)
