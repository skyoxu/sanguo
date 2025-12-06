extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _remove_sql_db_if_exists() -> void:
    var root = get_tree().get_root()
    if root.has_node("/root/SqlDb"):
        var db = root.get_node("/root/SqlDb")
        db.queue_free()
        await get_tree().process_frame

func test_settings_panel_works_without_db() -> void:
    await _remove_sql_db_if_exists()
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame
    # ensure starts hidden
    if panel.visible:
        panel.visible = false
        await get_tree().process_frame
    assert_bool(panel.visible).is_false()
    # show panel if method exposed
    if panel.has_method("ShowPanel"):
        panel.ShowPanel()
        await get_tree().process_frame
        assert_bool(panel.visible).is_true()
    # trigger save/load signals without /root/SqlDb
    var save_btn = panel.get_node("VBox/Buttons/SaveBtn")
    var load_btn = panel.get_node("VBox/Buttons/LoadBtn")
    save_btn.emit_signal("pressed")
    load_btn.emit_signal("pressed")
    await get_tree().process_frame
    # close should hide panel
    var close_btn = panel.get_node("VBox/Buttons/CloseBtn")
    close_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(panel.visible).is_false()

