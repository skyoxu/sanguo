extends GdUnitTestSuite

func _open_db()->bool:
    var db = get_node_or_null("/root/SqlDb")
    if db == null:
        push_warning("SKIP settings test: SqlDb not found")
        return false
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    if not db.TryOpen(path):
        push_warning("SKIP settings test: " + str(db.LastError))
        return false
    return true

func test_settings_save_and_load() -> void:
    if not _open_db():
        return
    var panel = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn").instantiate()
    add_child(panel)
    # set values
    var slider = panel.get_node("VBox/VolRow/VolSlider")
    slider.value = 0.7
    var gfx = panel.get_node("VBox/GraphicsRow/GraphicsOpt")
    if gfx.get_item_count() == 0:
        gfx.add_item("low"); gfx.add_item("medium"); gfx.add_item("high")
    gfx.selected = 2 # high
    var lang = panel.get_node("VBox/LangRow/LangOpt")
    if lang.get_item_count() == 0:
        lang.add_item("en"); lang.add_item("zh"); lang.add_item("ja")
    lang.selected = 1 # zh
    # save
    panel.get_node("VBox/Buttons/SaveBtn").emit_signal("pressed")
    # reset
    slider.value = 0.0
    gfx.selected = 0
    lang.selected = 0
    # load
    panel.get_node("VBox/Buttons/LoadBtn").emit_signal("pressed")
    await await_idle_frame()
    assert_float(float(slider.value)).is_greater(0.0)
    panel.queue_free()
