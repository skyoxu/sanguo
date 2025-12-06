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

func test_savegame_upsert_rollback_on_error() -> void:
    var path = "user://utdb_%s/save_err.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.CreateSchema()
    helper.ClearAll()

    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge))
    var username = "u_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertUser(username)).is_true()
    var uid = bridge.FindUserId(username)
    assert_that(uid).is_not_null()

    helper.SetEnv("DB_SIMULATE_SAVE_UPSERT_ERROR", "1")
    db.BeginTransaction()
    var ok_up = bridge.TryUpsertSave(uid, 1, '{"hp": 33}')
    db.RollbackTransaction()
    helper.SetEnv("DB_SIMULATE_SAVE_UPSERT_ERROR", "0")
    assert_bool(ok_up).is_false()

    var got = bridge.GetSaveData(uid, 1)
    assert_str(str(got)).is_empty()

