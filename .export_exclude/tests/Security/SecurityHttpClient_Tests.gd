extends GdUnitTestSuite

func _client() -> Node:
    var c = preload("res://Game.Godot/Scripts/Security/SecurityHttpClient.cs").new()
    add_child(c)
    return c

func test_rejects_http_protocol() -> void:
    var c = _client()
    var ok := c.Validate("GET", "http://example.com")
    assert_bool(ok).is_false()
    c.queue_free()

func test_rejects_unknown_domain() -> void:
    var c = _client()
    var ok := c.Validate("GET", "https://unknown.invalid")
    assert_bool(ok).is_false()
    c.queue_free()

func test_post_requires_content_type_and_size() -> void:
    var c = _client()
    var ok := c.Validate("POST", "https://example.com/api", "", 0)
    assert_bool(ok).is_false()
    ok = c.Validate("POST", "https://example.com/api", "application/json", 20000000)
    assert_bool(ok).is_false()
    c.queue_free()
