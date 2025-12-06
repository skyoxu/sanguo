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

func test_migration_ensure_min_version() -> void:
    var path = "user://utdb_%s/migrate.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.CreateSchema()
    # simulate downgrade
    var h2 = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(h2))
    h2.ExecSql("UPDATE schema_version SET version=0 WHERE id=1;")
    var before:int = helper.GetSchemaVersion()
    assert_int(before).is_less(1)
    helper.EnsureMinVersion(1)
    var after:int = helper.GetSchemaVersion()
    assert_int(after).is_greater_equal(1)
