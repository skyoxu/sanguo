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

static func _try_rename_abs(from_path: String, to_path: String) -> void:
    var err = DirAccess.rename_absolute(from_path, to_path)
    if err != OK:
        # fallback: copy + remove
        var rf = FileAccess.open(from_path, FileAccess.ModeFlags.READ)
        var wf = FileAccess.open(to_path, FileAccess.ModeFlags.WRITE)
        var size := rf.get_length()
        var buf = rf.get_buffer(size)
        wf.store_buffer(buf)
        rf.close(); wf.close()
        DirAccess.remove_absolute(from_path)

func test_close_rename_and_reopen_succeeds() -> void:
    var path = "user://utdb_%s/rename.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    _force_managed()
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    assert_bool(db.TryOpen(path)).is_true()
    var h = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(h))
    h.ExecSql("CREATE TABLE IF NOT EXISTS t(a INTEGER);")
    db.Close()
    await get_tree().process_frame
    var abs_old = _abs(path)
    var abs_new = abs_old.get_base_dir().path_join("renamed.db")
    _try_rename_abs(abs_old, abs_new)
    assert_bool(FileAccess.file_exists(abs_new)).is_true()
    var dir_user = path.get_base_dir()
    var new_user = dir_user.path_join("renamed.db")
    # reopen by new user:// path in same directory
    var db2 = await _new_db("SqlDb2")
    _force_managed()
    var ok = db2.TryOpen(new_user)
    assert_bool(ok).is_true()
