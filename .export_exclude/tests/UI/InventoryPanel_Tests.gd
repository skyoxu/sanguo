extends GdUnitTestSuite

func _open_datastore() -> bool:
    var ds = get_node_or_null("/root/DataStore")
    return ds != null

func test_inventory_save_and_load() -> void:
    if not _demo_enabled():
        push_warning("SKIP demo test: set TEMPLATE_DEMO=1 to enable")
        return
    if not _open_datastore():
        push_warning("SKIP inventory test: DataStore not found")
        return
    var inv = load("res://Game.Godot/Examples/UI/InventoryPanel.tscn").instantiate()
    add_child(inv)
    # add two items
    var add_btn = inv.get_node("VBox/Buttons/AddBtn")
    add_btn.emit_signal("pressed")
    add_btn.emit_signal("pressed")
    # save
    var save_btn = inv.get_node("VBox/Buttons/SaveBtn")
    save_btn.emit_signal("pressed")
    # clear and load
    var list = inv.get_node("VBox/Items")
    list.clear()
    var load_btn = inv.get_node("VBox/Buttons/LoadBtn")
    load_btn.emit_signal("pressed")
    await await_idle_frame()
    assert_int(list.item_count).is_greater(0)
    inv.queue_free()



