extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _new_db(name: String) -> Node:
    var db = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        db = Node.new()
        db.set_script(s)
    db.name = name
    get_tree().get_root().add_child(auto_free(db))
    return db

func test_inventory_merge_and_clear_cross_restart() -> void:
    var path = "user://utdb_%s/inv2.db" % Time.get_unix_time_from_system()
    var db = _new_db("SqlDb")
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.CreateSchema()
    helper.ClearAll()

    var inv = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(inv))
    assert_bool(inv.Add("potion", 2)).is_true()
    assert_bool(inv.Add("potion", 3)).is_true()
    var items = inv.All()
    var merged := false
    for s in items:
        if str(s).find("potion:5") != -1:
            merged = true
            break
    assert_bool(merged).is_true()

    # close and reopen same node/path
    db.Close()
    await get_tree().process_frame
    var ok2 = db.TryOpen(path)
    assert_bool(ok2).is_true()

    var inv2 = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(inv2))
    var items2 = inv2.All()
    var persisted := false
    for s in items2:
        if str(s).find("potion:5") != -1:
            persisted = true
            break
    assert_bool(persisted).is_true()

    # clear and verify empty across restart
    helper.ClearAll()
    db.Close()
    await get_tree().process_frame
    var ok3 = db.TryOpen(path)
    assert_bool(ok3).is_true()
    var inv3 = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(inv3))
    var items3 = inv3.All()
    assert_int(items3.size()).is_equal(0)
