extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _new_db(name: String) -> Node:
    var db = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        if s == null or not s.has_method("new"):
            push_warning("SKIP: CSharpScript.new() unavailable, skip DB new")
            return null
        db = s.new()
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

func test_transaction_rollback_inventory() -> void:
    var path = "user://utdb_%s/trx_inv.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.CreateSchema()
    helper.ClearAll()

    db.BeginTransaction()
    var inv = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(inv))
    assert_bool(inv.Add("potion", 1)).is_true()
    db.RollbackTransaction()
    var items = inv.All()
    var found := false
    for s in items:
        if str(s).find("potion:") != -1:
            found = true
            break
    assert_bool(found).is_false()

func test_transaction_commit_savegame() -> void:
    var path = "user://utdb_%s/trx_sg.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.CreateSchema()
    helper.ClearAll()

    db.BeginTransaction()
    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge))
    var username = "u_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertUser(username)).is_true()
    var uid = bridge.FindUserId(username)
    assert_that(uid).is_not_null()
    var json = '{"hp": 11, "ts": %d}' % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertSave(uid, 1, json)).is_true()
    db.CommitTransaction()

    var bridge2 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge2))
    var got = bridge2.GetSaveData(uid, 1)
    assert_str(str(got)).contains('"hp": 11')

func test_journal_mode_delete() -> void:
    var path = "user://utdb_%s/journal.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    var helper = _force_managed() # sets GD_DB_JOURNAL=DELETE
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    # Query PRAGMA journal_mode and expect delete
    # Verify no WAL sidecar created under DELETE mode
    assert_bool(FileAccess.file_exists(path + "-wal")).is_false()
