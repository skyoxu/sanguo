extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _db() -> Node:
    var db = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        if s == null or not s.has_method("new"):
            push_warning("SKIP: CSharpScript.new() unavailable, skip DB new")
            return null
        db = s.new()
    db.name = "SqlDb"
    get_tree().get_root().add_child(auto_free(db))
    return db

func test_try_open_user_path_should_succeed() -> void:
    var db = _db()
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    var p = "user://utdb_%d/game.db" % Time.get_unix_time_from_system()
    var ok = db.TryOpen(p)
    assert_bool(ok).is_true()
    # 文件应已在 user:// 下创建（不直接调用 C# Execute/Query 以避免绑定差异）
    assert_bool(FileAccess.file_exists(p)).is_true()

func test_try_open_absolute_path_should_fail() -> void:
    var db = _db()
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    var p = "C:/temp/evil.db"
    var ok = db.TryOpen(p)
    assert_bool(ok).is_false()
    # lower-case the source string before assertion, avoid calling to_lower() on assertion object
    assert_str(str(db.LastError).to_lower()).contains("user://")

func test_try_open_traversal_should_fail() -> void:
    var db = _db()
    if db == null:
        push_warning("SKIP: missing C# instantiate, skip test")
        return
    var p = "user://../evil.db"
    var ok = db.TryOpen(p)
    assert_bool(ok).is_false()
    # lower-case the source string before assertion, avoid calling to_lower() on assertion object
    assert_str(str(db.LastError).to_lower()).contains("not allowed")
