extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _new_db(name: String) -> Node:
    var db: Node = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        db = Node.new()
        db.set_script(s)
    db.name = name
    get_tree().get_root().add_child(auto_free(db))
    await get_tree().process_frame
    if not db.has_method("TryOpen"):
        await get_tree().process_frame
    return db


func _today_dir() -> String:
    var d = Time.get_datetime_dict_from_system()
    return "%04d-%02d-%02d" % [d.year, d.month, d.day]


func _audit_path() -> String:
    return "res://logs/ci/%s/security-audit.jsonl" % _today_dir()


func _remove_audit_file() -> void:
    var p: String = _audit_path()
    if FileAccess.file_exists(p):
        var abs: String = ProjectSettings.globalize_path(p)
        DirAccess.remove_absolute(abs)


func test_open_denied_writes_audit_log() -> void:
    _remove_audit_file()

    var db = await _new_db("DbAuditOpenFail")
    var ok: bool = db.TryOpen("C:/temp/security_open_denied.db")
    assert_bool(ok).is_false()

    await get_tree().process_frame

    var p: String = _audit_path()
    assert_bool(FileAccess.file_exists(p)).is_true()

    var txt: String = FileAccess.get_file_as_string(p)
    assert_str(txt).is_not_empty()

    var lines: Array = txt.split("\n", false)
    var found := false
    for i in range(lines.size()):
        var raw: String = lines[i].strip_edges()
        if raw == "":
            continue
        var parsed = JSON.parse_string(raw)
        if parsed == null:
            continue
        var action = str(parsed.get("action", "")).to_lower()
        if action == "db.open.fail":
            found = true
            break

    assert_bool(found).is_true()
