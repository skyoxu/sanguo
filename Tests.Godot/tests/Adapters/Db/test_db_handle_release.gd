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

func _force_managed() -> void:
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.ForceManaged()

func _abs(p: String) -> String:
    return ProjectSettings.globalize_path(p)

func test_handle_released_after_close_allows_rw_open() -> void:
    var path = "user://utdb_%s/handle.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    # create small write to ensure file exists
    var h = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(h))
    h.ExecSql("CREATE TABLE IF NOT EXISTS t(a INTEGER);")
    db.Close()
    await get_tree().process_frame
    var f = FileAccess.open(_abs(path), FileAccess.ModeFlags.READ_WRITE)
    assert_that(f).is_not_null()
    if f:
        f.close()
