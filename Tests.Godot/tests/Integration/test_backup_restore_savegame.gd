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

static func _mkdirs_user(abs_path: String) -> bool:
    var base := abs_path.get_base_dir()
    if not base.begins_with("user://"):
        return false
    var rel := base.substr("user://".length())
    var d := DirAccess.open("user://")
    if d == null:
        return false
    return d.make_dir_recursive(rel) == OK

static func _copy_file(src: String, dst: String) -> bool:
    if not _mkdirs_user(dst):
        return false
    var r := FileAccess.open(src, FileAccess.READ)
    if r == null:
        return false
    var data := r.get_buffer(r.get_length())
    var w := FileAccess.open(dst, FileAccess.WRITE)
    if w == null:
        return false
    w.store_buffer(data)
    var wal := src + "-wal"
    var shm := src + "-shm"
    if FileAccess.file_exists(wal):
        var rw := FileAccess.open(wal, FileAccess.READ)
        if rw != null:
            var dw := FileAccess.open(dst + "-wal", FileAccess.WRITE)
            if dw != null:
                dw.store_buffer(rw.get_buffer(rw.get_length()))
    if FileAccess.file_exists(shm):
        var rs := FileAccess.open(shm, FileAccess.READ)
        if rs != null:
            var ds := FileAccess.open(dst + "-shm", FileAccess.WRITE)
            if ds != null:
                ds.store_buffer(rs.get_buffer(rs.get_length()))
    return true

func test_backup_restore_savegame() -> void:
    var path = "user://utdb_%s/sg_bak.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    # Force managed provider
    var helper_sc = load("res://Game.Godot/Adapters/Db/DbTestHelper.cs")
    if helper_sc == null or not helper_sc.has_method("new"):
        push_warning("SKIP: helper C# unavailable, skip")
        return
    var helper = helper_sc.new()
    add_child(auto_free(helper))
    helper.ForceManaged()
    var tries := 20
    while not db.has_method("TryOpen") and tries > 0:
        await get_tree().process_frame
        tries -= 1
    assert_bool(db.has_method("TryOpen")).is_true()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    helper.ExecSql("PRAGMA journal_mode=DELETE;")
    # Ensure schema exists and clean
    helper.CreateSchema()
    helper.ClearAll()

    var bridge_sc = load("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs")
    if bridge_sc == null or not bridge_sc.has_method("new"):
        push_warning("SKIP: RepositoryTestBridge C# unavailable, skip")
        return
    var bridge = bridge_sc.new()
    add_child(auto_free(bridge))
    var username = "u_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertUser(username)).is_true()
    var uid = bridge.FindUserId(username)
    assert_that(uid).is_not_null()
    var json = '{"hp": 55, "ts": %d}' % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertSave(uid, 1, json)).is_true()

    # checkpoint WAL → close → copy to backup
    helper.ExecSql("PRAGMA wal_checkpoint(TRUNCATE);")
    db.Close()
    await get_tree().process_frame
    var backup_dir = "user://backup_%s" % Time.get_unix_time_from_system()
    var backup_path = "%s/%s" % [backup_dir, path.get_file()]
    assert_bool(_copy_file(path, backup_path)).is_true()

    # open from backup and verify
    tries = 10
    while not db.has_method("TryOpen") and tries > 0:
        await get_tree().process_frame
        tries -= 1
    assert_bool(db.has_method("TryOpen")).is_true()
    var ok2 = db.TryOpen(backup_path)
    assert_bool(ok2).is_true()
    # schema fallback to avoid Nil if copy missed table (tests only)
    if db.has_method("TableExists") and not db.TableExists("saves"):
        helper.CreateSchema()
    var bridge2_sc = load("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs")
    if bridge2_sc == null or not bridge2_sc.has_method("new"):
        push_warning("SKIP: RepositoryTestBridge C# unavailable, skip")
        return
    var bridge2 = bridge2_sc.new()
    add_child(auto_free(bridge2))
    await get_tree().process_frame
    var got = bridge2.GetSaveData(uid, 1)
    assert_str(str(got)).contains('"hp": 55')

