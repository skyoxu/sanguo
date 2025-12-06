extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _client() -> Node:
    var sc = load("res://Game.Godot/Scripts/Security/SecurityHttpClient.cs")
    if sc == null or not sc.has_method("new"):
        push_warning("SKIP: CSharpScript.new() unavailable, skip SecurityHttpClient tests")
        return null
    var c = sc.new()
    add_child(auto_free(c))
    return c

func test_rejects_http_protocol() -> void:
    var c = _client()
    if c == null: return
    var ok = c.Validate("GET", "http://example.com", "", 0)
    assert_bool(ok).is_false()

func test_rejects_unknown_domain() -> void:
    var c = _client()
    if c == null: return
    var ok = c.Validate("GET", "https://unknown.invalid", "", 0)
    assert_bool(ok).is_false()

func test_post_requires_content_type_and_size() -> void:
    var c = _client()
    if c == null: return
    var ok = c.Validate("POST", "https://example.com/api", "", 0)
    assert_bool(ok).is_false()
    ok = c.Validate("POST", "https://example.com/api", "application/json", 20000000)
    assert_bool(ok).is_false()

