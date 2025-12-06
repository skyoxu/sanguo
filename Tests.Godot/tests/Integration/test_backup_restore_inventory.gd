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
    # copy sqlite sidecars if exist (WAL/SHM)
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

func test_backup_restore_inventory() -> void:
    var path = "user://utdb_%s/inv_bak.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    # Force managed provider to avoid flaky plugin path
    var helper_sc = load("res://Game.Godot/Adapters/Db/DbTestHelper.cs")
    if helper_sc == null or not helper_sc.has_method("new"):
        push_warning("SKIP: helper C# script unavailable, skip")
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

    # Add inventory items via repo bridge (guard C#)
    var inv_sc = load("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs")
    if inv_sc == null or not inv_sc.has_method("new"):
        push_warning("SKIP: InventoryRepoBridge C# unavailable, skip")
        return
    var inv = inv_sc.new()
    add_child(auto_free(inv))
    assert_bool(inv.Add("potion", 3)).is_true()
    assert_bool(inv.Add("elixir", 2)).is_true()

    # checkpoint WAL then close and copy to backup
    helper.ExecSql("PRAGMA wal_checkpoint(TRUNCATE);")
    db.Close()
    await get_tree().process_frame
    var backup_dir = "user://backup_%s" % Time.get_unix_time_from_system()
    var backup_path = "%s/%s" % [backup_dir, path.get_file()]
    assert_bool(_copy_file(path, backup_path)).is_true()

    # open from backup and verify items present
    tries = 10
    while not db.has_method("TryOpen") and tries > 0:
        await get_tree().process_frame
        tries -= 1
    assert_bool(db.has_method("TryOpen")).is_true()
    var ok2 = db.TryOpen(backup_path)
    assert_bool(ok2).is_true()
    # schema fallback to avoid Nil if copy missed table (tests only)
    if db.has_method("TableExists") and not db.TableExists("inventory_items"):
        helper.CreateSchema()
    var inv2_sc = load("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs")
    if inv2_sc == null or not inv2_sc.has_method("new"):
        push_warning("SKIP: InventoryRepoBridge C# unavailable, skip")
        return
    var inv2 = inv2_sc.new()
    add_child(auto_free(inv2))
    await get_tree().process_frame
    var items = inv2.All()
    var ok_p := false
    var ok_e := false
    for s in items:
        if str(s).find("potion:3") != -1:
            ok_p = true
        if str(s).find("elixir:2") != -1:
            ok_e = true
    assert_bool(ok_p and ok_e).is_true()

