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


func test_emits_request_blocked_signal_on_denied() -> void:
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

