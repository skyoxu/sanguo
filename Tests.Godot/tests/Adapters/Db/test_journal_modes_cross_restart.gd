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

func _force_managed() -> Node:
    if _db_helper == null:
        _db_helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
        add_child(auto_free(_db_helper))
        await get_tree().process_frame
    _db_helper.ForceManaged()
    return _db_helper

func _abs(p: String) -> String:
    return ProjectSettings.globalize_path(p)

func test_wal_creates_wal_sidecar_and_delete_mode_not() -> void:
    # WAL
    var helper = await _force_managed()
    helper.SetEnv("GD_DB_JOURNAL", "WAL")
    var wal_path = "user://utdb_%s/journal_wal.db" % Time.get_unix_time_from_system()
    var db1 = await _new_db("SqlDb")
    assert_bool(db1.TryOpen(wal_path)).is_true()
    _db_helper.ExecOnNode("SqlDb", "CREATE TABLE IF NOT EXISTS t(a INTEGER);")
    _db_helper.ExecOnNode("SqlDb", "INSERT INTO t(a) VALUES(1);")
    await get_tree().process_frame
    assert_bool(FileAccess.file_exists(_abs(wal_path) + "-wal")).is_true()
    db1.Close()

    # DELETE (no -wal expected)
    helper.SetEnv("GD_DB_JOURNAL", "DELETE")
    var del_path = "user://utdb_%s/journal_del.db" % Time.get_unix_time_from_system()
    var db2 = await _new_db("SqlDb2")
    assert_bool(db2.TryOpen(del_path)).is_true()
    _db_helper.ExecOnNode("SqlDb2", "CREATE TABLE IF NOT EXISTS t(a INTEGER);")
    _db_helper.ExecOnNode("SqlDb2", "INSERT INTO t(a) VALUES(1);")
    await get_tree().process_frame
    assert_bool(FileAccess.file_exists(_abs(del_path) + "-wal")).is_false()
    db2.Close()
