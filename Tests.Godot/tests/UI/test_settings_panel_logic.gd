extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CFG_PATH := "user://settings.cfg"

func _clear_config() -> void:
    var dir := DirAccess.open("user://")
    if dir and dir.file_exists("settings.cfg"):
        dir.remove("settings.cfg")

# ACC:T29.2
func test_settings_save_and_load_via_configfile() -> void:
    var original_locale := ""
    if TranslationServer.has_method("get_locale"):
        original_locale = String(TranslationServer.get_locale())

    _clear_config()
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn") as PackedScene
    assert_bool(packed != null).is_true()
    if packed == null:
        if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
            TranslationServer.set_locale(original_locale)
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame

    # set values
    var slider = panel.get_node("Center/VBox/VolRow/VolSlider")
    slider.value = 0.7
    var gfx = panel.get_node("Center/VBox/GraphicsRow/GraphicsOpt")
    if gfx.get_item_count() == 0:
        gfx.add_item("low"); gfx.add_item("medium"); gfx.add_item("high")
    gfx.select(2) # high
    var lang = panel.get_node("Center/VBox/LangRow/LangOpt")
    if lang.get_item_count() == 0:
        lang.add_item("en"); lang.add_item("zh"); lang.add_item("ja")
    lang.select(1) # zh
    var res_opt = panel.get_node("Center/VBox/ResolutionRow/ResolutionOpt")
    if res_opt.get_item_count() == 0:
        res_opt.add_item("1280x720"); res_opt.add_item("1600x900")
    res_opt.select(0)
    var mode_opt = panel.get_node("Center/VBox/WindowModeRow/WindowModeOpt")
    if mode_opt.get_item_count() == 0:
        mode_opt.add_item("windowed"); mode_opt.add_item("fullscreen")
    mode_opt.select(0)

    # save (to ConfigFile)
    panel.get_node("Center/VBox/Buttons/SaveBtn").emit_signal("pressed")
    await get_tree().process_frame

    # validate persisted ConfigFile keys
    var cfg := ConfigFile.new()
    var err := cfg.load(CFG_PATH)
    assert_int(err).is_equal(OK)
    assert_float(float(cfg.get_value("settings", "vol", 0.0))).is_equal(0.7)
    assert_str(str(cfg.get_value("settings", "gfx", ""))).is_equal("high")
    assert_str(str(cfg.get_value("settings", "lang", ""))).is_equal("zh")
    var saved_res := str(cfg.get_value("settings", "resolution", ""))
    var saved_mode := str(cfg.get_value("settings", "window_mode", ""))
    assert_str(saved_res).is_equal("1280x720")
    assert_str(saved_mode).is_equal("windowed")

    # reset in-memory selections
    slider.value = 0.0
    gfx.select(0)
    lang.select(0)
    res_opt.select(min(1, res_opt.get_item_count() - 1))
    mode_opt.select(min(1, mode_opt.get_item_count() - 1))

    # load (from ConfigFile)
    panel.call("ShowPanel")
    await get_tree().process_frame
    assert_bool(abs(float(slider.value) - 0.7) < 0.0001).is_true()
    assert_str(str(gfx.get_item_metadata(gfx.selected))).is_equal("high")
    assert_str(str(lang.get_item_metadata(lang.selected))).is_equal("zh")
    assert_str(res_opt.get_item_text(res_opt.selected)).is_equal(saved_res)
    assert_str(str(mode_opt.get_item_metadata(mode_opt.selected))).is_equal(saved_mode)
    panel.queue_free()
    if TranslationServer.has_method("set_locale") and original_locale.strip_edges().length() > 0:
        TranslationServer.set_locale(original_locale)
