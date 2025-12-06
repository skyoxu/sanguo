extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func before() -> void:
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.ForceManaged()
    var db = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        db = Node.new()
        db.set_script(s)
    db.name = "SqlDb"
    get_tree().get_root().add_child(auto_free(db))
    var path := "user://utdb_%s/game.db" % Time.get_unix_time_from_system()
    if not db.TryOpen(path):
        push_warning("SKIP: " + str(db.LastError))
        return
    helper.CreateSchema()
    helper.ClearAll()

func test_savegame_upsert_and_get() -> void:
    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge))
    var _ok = bridge.UpsertUser("bob")
    var uid = bridge.FindUserId("bob")
    assert_that(uid).is_not_null()
    var json := "{\"hp\":100}"
    var ok2 = bridge.UpsertSave(uid, 1, json)
    assert_bool(ok2).is_true()
    var got = bridge.GetSaveData(uid, 1)
    assert_str(str(got)).contains("hp")
