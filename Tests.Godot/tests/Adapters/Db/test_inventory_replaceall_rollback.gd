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
    await get_tree().process_frame
    if not db.has_method("TryOpen"):
        await get_tree().process_frame
    return db

func _force_managed() -> Node:
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.ForceManaged()
    return helper

func test_inventory_replaceall_rollback_on_error() -> void:
    var path = "user://utdb_%s/replaceall_err.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.CreateSchema()
    helper.ClearAll()
    helper.SetEnv("DB_SIMULATE_REPLACEALL_ERROR", "1")
    var inv = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(inv))
    var done = inv.TryReplaceAllToSingle("potion", 5)
    helper.SetEnv("DB_SIMULATE_REPLACEALL_ERROR", "0")
    assert_bool(done).is_false()
    var items = inv.All()
    var found := false
    for s in items:
        if str(s).find("potion:") != -1:
            found = true
            break
    assert_bool(found).is_false()

