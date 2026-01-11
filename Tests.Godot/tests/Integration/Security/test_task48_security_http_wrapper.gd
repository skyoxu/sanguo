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

func _read_last_non_empty_line(path: String) -> String:
    var txt := FileAccess.get_file_as_string(path)
    assert_str(txt).is_not_empty()
    var lines := txt.split("\n", false)
    for i in range(lines.size() - 1, -1, -1):
        var l := lines[i].strip_edges()
        if l != "":
            return l
    assert_bool(false).is_true()
    return ""

# ACC:T48.6
func test_allow_https_host_writes_audit_jsonl() -> void:
    _remove_audit_file()
    var c = _client()
    OS.set_environment("ALLOWED_EXTERNAL_HOSTS", "example.com")
    var ok = c.Validate("GET", "https://example.com/api", "", 0)
    assert_bool(ok).is_true()
    await get_tree().process_frame
    var p := _audit_path()
    assert_bool(FileAccess.file_exists(p)).is_true()
    var obj = JSON.parse_string(_read_last_non_empty_line(p))
    assert_that(obj).is_not_null()
    assert_str(str(obj["event_type"]).to_upper()).is_equal("HTTP_ALLOWED")
    assert_str(str(obj["url"])).starts_with("https://")

# ACC:T48.6
func test_deny_http_protocol_writes_audit_jsonl() -> void:
    _remove_audit_file()
    var c = _client()
    OS.set_environment("ALLOWED_EXTERNAL_HOSTS", "example.com")
    var ok = c.Validate("GET", "http://example.com", "", 0)
    assert_bool(ok).is_false()
    await get_tree().process_frame
    var p := _audit_path()
    assert_bool(FileAccess.file_exists(p)).is_true()
    var obj = JSON.parse_string(_read_last_non_empty_line(p))
    assert_that(obj).is_not_null()
    assert_str(str(obj["event_type"]).to_lower()).contains("protocol_denied")
    assert_str(str(obj["url"])).starts_with("http://")

# ACC:T48.6
func test_invalid_url_writes_audit_jsonl() -> void:
    _remove_audit_file()
    var c = _client()
    OS.set_environment("ALLOWED_EXTERNAL_HOSTS", "example.com")
    var ok = c.Validate("GET", "https://exa mple.com", "", 0)
    assert_bool(ok).is_false()
    await get_tree().process_frame
    var p := _audit_path()
    assert_bool(FileAccess.file_exists(p)).is_true()
    var obj = JSON.parse_string(_read_last_non_empty_line(p))
    assert_that(obj).is_not_null()
    assert_str(str(obj["event_type"]).to_lower()).contains("parse_error")

# ACC:T48.6
func test_denied_request_emits_request_blocked_signal() -> void:
    var c = _client()
    OS.set_environment("ALLOWED_EXTERNAL_HOSTS", "example.com")

    var blocked_reason := ""
    var blocked_url := ""

    c.RequestBlocked.connect(func(reason: String, url: String) -> void:
        blocked_reason = reason
        blocked_url = url
    )

    var ok = c.Validate("GET", "http://example.com", "", 0)
    assert_bool(ok).is_false()

    await get_tree().process_frame

    assert_str(blocked_reason).is_not_empty()
    assert_str(blocked_url).starts_with("http://")
