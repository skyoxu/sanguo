extends GdUnitTestSuite

func _open_test_db() -> bool:
    var db = get_node_or_null("/root/SqlDb")
    if db == null:
        push_warning("SKIP repo test: SqlDb not found")
        return false
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    if not db.TryOpen(path):
        push_warning("SKIP repo test: " + str(db.LastError))
        return false
    return true

func test_savegame_upsert_and_get() -> void:
    if not _open_test_db():
        return
    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(bridge)
    var _ok := bridge.UpsertUser("bob")
    var uid := bridge.FindUserId("bob")
    assert_object(uid).is_not_null()
    var json := "{\"hp\":100}"
    var ok2 := bridge.UpsertSave(uid, 1, json)
    assert_bool(ok2).is_true()
    var got := bridge.GetSaveData(uid, 1)
    assert_str(str(got)).contains("hp")
    bridge.queue_free()
