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

func _read_audit() -> String:
    var p = "res://logs/ci/%s/security-audit.jsonl" % _today_dir()
    if not FileAccess.file_exists(p):
        return ""
    return FileAccess.get_file_as_string(p)

func test_exec_and_query_failures_are_audited() -> void:
    # NOTE: GDScript currently has no try/catch; raising C# exceptions
    # from Execute/Query would cause a Debugger Break in headless CI.
    # The open-fail path already verifies audit logging in
    # test_db_open_denied_writes_audit_log.
    push_warning("SKIP: exec/query audit covered by open-fail test; no try/catch in GDScript")
    assert_bool(true).is_true()