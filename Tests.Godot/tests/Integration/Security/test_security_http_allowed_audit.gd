extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _client() -> Node:
    var sc = load("res://Game.Godot/Scripts/Security/SecurityHttpClient.cs")
    assert_that(sc).is_not_null()
    var c: Node
    if sc.has_method("new"):
        c = sc.new()
    else:
        c = Node.new()
        c.set_script(sc)
    add_child(auto_free(c))
    return c

func _audit_path() -> String:
    return "user://logs/security/audit-http.jsonl"

func _remove_audit_file() -> void:
    var p := _audit_path()
    if FileAccess.file_exists(p):
        var abs := ProjectSettings.globalize_path(p)
        DirAccess.remove_absolute(abs)

func test_audit_written_on_allow() -> void:
    _remove_audit_file()
    var c = _client()
    OS.set_environment("ALLOWED_EXTERNAL_HOSTS", "example.com")
    var ok = c.Validate("GET", "https://example.com/api", "", 0)
    assert_bool(ok).is_true()
    await get_tree().process_frame
    var p := _audit_path()
    assert_bool(FileAccess.file_exists(p)).is_true()
    var txt := FileAccess.get_file_as_string(p)
    assert_str(txt).is_not_empty()
    var lines := txt.split("\n", false)
    var last := ""
    for i in range(lines.size()-1, -1, -1):
        var l := lines[i].strip_edges()
        if l != "":
            last = l
            break
    assert_str(last).is_not_empty()
    var obj = JSON.parse_string(last)
    assert_that(obj).is_not_null()
    assert_str(str(obj["event_type"]).to_upper()).is_equal("HTTP_ALLOWED")
    assert_str(str(obj["url"])).starts_with("https://")
