extends GdUnitTestSuite

func _open_db() -> bool:
    var db = get_node_or_null("/root/SqlDb")
    if db == null:
        push_warning("SKIP inventory repo test: SqlDb not found")
        return false
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    if not db.TryOpen(path):
        push_warning("SKIP inventory repo test: " + str(db.LastError))
        return false
    return true

func test_inventory_panel_repo_save_load() -> void:
    if not _demo_enabled():
        push_warning("SKIP demo test: set TEMPLATE_DEMO=1 to enable")
        return
    if not _open_db():
        return
    var inv = load("res://Game.Godot/Examples/UI/InventoryPanel.tscn").instantiate()
    add_child(inv)
    inv.UseRepository = true
    # add items
    var add_btn = inv.get_node("VBox/Buttons/AddBtn")
    add_btn.emit_signal("pressed")
    add_btn.emit_signal("pressed")
    # save
    inv.get_node("VBox/Buttons/SaveBtn").emit_signal("pressed")
    # clear and load
    var list = inv.get_node("VBox/Items")
    list.clear()
    inv.get_node("VBox/Buttons/LoadBtn").emit_signal("pressed")
    await await_idle_frame()
    assert_int(list.item_count).is_greater(0)
    inv.queue_free()



