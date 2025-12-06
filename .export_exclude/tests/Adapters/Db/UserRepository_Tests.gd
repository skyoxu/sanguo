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

func test_user_upsert_and_find() -> void:
    if not _open_test_db():
        return
    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(bridge)
    var ok := bridge.UpsertUser("alice")
    assert_bool(ok).is_true()
    var name := bridge.FindUser("alice")
    assert_str(str(name)).is_equal("alice")
    bridge.queue_free()
