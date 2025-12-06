extends GdUnitTestSuite

func _open_test_db() -> bool:
    var db = get_node_or_null("/root/SqlDb")
    if db == null:
        push_warning("SKIP inv repo test: SqlDb not found")
        return false
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    if not db.TryOpen(path):
        push_warning("SKIP inv repo test: " + str(db.LastError))
        return false
    return true

func test_inventory_add_and_list() -> void:
    if not _open_test_db():
        return
    var bridge = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(bridge)
    var ok := bridge.Add("potion", 2)
    assert_bool(ok).is_true()
    var items := bridge.All()
    assert_int(int(items.size())).is_greater(0)
    bridge.queue_free()
