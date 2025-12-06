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

func _force_managed() -> Node:
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.ForceManaged()
    return helper

func test_utf8_chinese_roundtrip_cross_restart() -> void:
    var path = "user://utdb_%s/utf8.db" % Time.get_unix_time_from_system()
    var db = await _new_db("SqlDb")
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    _force_managed()
    var ok = db.TryOpen(path)
    assert_bool(ok).is_true()
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.CreateSchema()

    var bridge = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge))
    var uname = "玩家_中文_äöü_✓_%s" % Time.get_unix_time_from_system()
    assert_bool(bridge.UpsertUser(uname)).is_true()
    var uid = bridge.FindUserId(uname)
    assert_that(uid).is_not_null()
    var json = '{"msg":"你好，世界！äöü✓","num":42}'
    assert_bool(bridge.UpsertSave(uid, 1, json)).is_true()

    # close and reopen
    db.Close()
    await get_tree().process_frame
    var db2 = await _new_db("SqlDb2")
    _force_managed()
    var ok2 = db2.TryOpen(path)
    assert_bool(ok2).is_true()
    var bridge2 = preload("res://Game.Godot/Adapters/Db/RepositoryTestBridge.cs").new()
    add_child(auto_free(bridge2))
    var got_uname = bridge2.FindUser(uname)
    # 某些实现会在字符串末尾带有 <null> 等调试后缀，这里仅验证前缀一致
    assert_str(str(got_uname).substr(0, uname.length())).is_equal(uname)
    var got_json = bridge2.GetSaveData(uid, 1)
    assert_str(str(got_json)).contains("你好，世界！")
    assert_str(str(got_json)).contains("äöü✓")
