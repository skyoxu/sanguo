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

func test_savegame_cross_restart_persists() -> void:
    var path = "user://utdb_%s/save.db" % Time.get_unix_time_from_system()
    var db = _new_db("SqlDb")
    var ok1 = db.TryOpen(path)
    assert_bool(ok1).is_true()
    # Ensure schema exists
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.CreateSchema()
    # Create user and save
    var bridge1 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge1))
    var username = "sg_user_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge1.UpsertUser(username)).is_true()
    var uid = bridge1.FindUserId(username)
    assert_that(uid).is_not_null()
    var json = '{"hp": 88, "ts": %d}' % Time.get_unix_time_from_system()
    assert_bool(bridge1.UpsertSave(uid, 1, json)).is_true()
    db.Close()
    await get_tree().process_frame

    # Reopen and verify save persists using same node
    var ok2 = db.TryOpen(path)
    assert_bool(ok2).is_true()
    var bridge2 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge2))
    var got = bridge2.GetSaveData(uid, 1)
    assert_str(str(got)).contains("hp")
