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

var _db_helper = null

func _force_managed() -> void:
    if _db_helper == null:
        _db_helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
        add_child(auto_free(_db_helper))
        await get_tree().process_frame
    _db_helper.ForceManaged()

func test_concurrent_read_after_write_commit() -> void:
    var path = "user://utdb_%s/concurrent.db" % Time.get_unix_time_from_system()
    await _force_managed()
    var a = await _new_db("SqlDbA")
    var b = await _new_db("SqlDbB")
    if a == null or b == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    assert_bool(a.TryOpen(path)).is_true()
    assert_bool(b.TryOpen(path)).is_true()
    _db_helper.ExecOnNode("SqlDbA", "CREATE TABLE IF NOT EXISTS t(k TEXT PRIMARY KEY, v INTEGER);")
    _db_helper.ExecOnNode("SqlDbA", "INSERT OR REPLACE INTO t(k,v) VALUES('key',7);")
    await get_tree().process_frame
    var value = _db_helper.QueryOnNode2("SqlDbB", "SELECT v FROM t WHERE k=@0;", "key")
    assert_int(value).is_equal(7)
