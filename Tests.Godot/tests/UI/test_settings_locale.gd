extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T205.4
func test_supported_locale_switch_updates_visible_settings_text_and_missing_key_falls_back() -> void:
    var original_locale := ""
    if TranslationServer.has_method("get_locale"):
        original_locale = String(TranslationServer.get_locale())

    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    assert_object(packed).is_not_null()
    if packed == null:
        if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
            TranslationServer.set_locale(original_locale)
        return

    TranslationServer.set_locale("en")
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame

    var lang_label = panel.get_node("Center/VBox/LangRow/LangLabel") as Label
    var save_btn = panel.get_node("Center/VBox/Buttons/SaveBtn") as Button
    assert_object(lang_label).is_not_null()
    assert_object(save_btn).is_not_null()
    assert_str(lang_label.text).is_equal("Language")
    assert_str(save_btn.text).is_equal("Save")

    var lang_opt = panel.get_node("Center/VBox/LangRow/LangOpt") as OptionButton
    assert_object(lang_opt).is_not_null()
    var zh_idx := -1
    for i in range(lang_opt.get_item_count()):
        if str(lang_opt.get_item_metadata(i)).to_lower() == "zh":
            zh_idx = i
            break
    assert_bool(zh_idx >= 0).is_true()
    if zh_idx >= 0:
        lang_opt.select(zh_idx)
        lang_opt.emit_signal("item_selected", zh_idx)
        await get_tree().process_frame
        assert_str(TranslationServer.get_locale()).contains("zh")
        assert_str(lang_label.text).is_equal("语言")
        assert_str(save_btn.text).is_equal("保存")

    TranslationServer.set_locale("zz")
    panel.call("ShowPanel")
    await get_tree().process_frame
    assert_str(lang_label.text).is_not_empty()
    assert_str(lang_label.text).not_contains("ui.settings.language")

    if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
        TranslationServer.set_locale(original_locale)

func test_language_applies_runtime() -> void:
    var original_locale := ""
    if TranslationServer.has_method("get_locale"):
        original_locale = String(TranslationServer.get_locale())

    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
            TranslationServer.set_locale(original_locale)
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    var lang_opt = panel.get_node("Center/VBox/LangRow/LangOpt") as OptionButton
    if lang_opt.get_item_count() == 0:
        lang_opt.add_item("en"); lang_opt.add_item("zh")
    # select zh and emit selection
    var idx := -1
    for i in range(lang_opt.get_item_count()):
        if str(lang_opt.get_item_metadata(i)).to_lower() == "zh":
            idx = i
            break
        if str(lang_opt.get_item_text(i)).to_lower() == "zh":
            idx = i
            break
    if idx == -1:
        push_warning("SKIP: zh option not found")
        if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
            TranslationServer.set_locale(original_locale)
        return
    lang_opt.select(idx)
    lang_opt.emit_signal("item_selected", idx)
    await get_tree().process_frame
    assert_str(TranslationServer.get_locale()).contains("zh")
    if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
        TranslationServer.set_locale(original_locale)
