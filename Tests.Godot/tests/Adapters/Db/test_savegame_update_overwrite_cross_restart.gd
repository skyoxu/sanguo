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

func test_savegame_update_overwrite_cross_restart() -> void:
    var path = "user://utdb_%s/save2.db" % Time.get_unix_time_from_system()
    var db = _new_db("SqlDb")
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.CreateSchema()
    helper.ClearAll()

    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge))
    var username = "u_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertUser(username)).is_true()
    var uid = bridge.FindUserId(username)
    assert_that(uid).is_not_null()

    var json1 = '{"hp": 42, "ts": %d}' % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertSave(uid, 1, json1)).is_true()
    db.Close()
    await get_tree().process_frame

    var ok2 = db.TryOpen(path)
    assert_bool(ok2).is_true()
    var bridge2 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge2))
    var json2 = '{"hp": 77, "ts": %d}' % Time.get_unix_time_from_system()
    assert_bool(bridge2.UpsertSave(uid, 1, json2)).is_true()
    db.Close()
    await get_tree().process_frame

    var ok3 = db.TryOpen(path)
    assert_bool(ok3).is_true()
    var bridge3 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge3))
    var got = bridge3.GetSaveData(uid, 1)
    assert_str(str(got)).contains('"hp": 77')
