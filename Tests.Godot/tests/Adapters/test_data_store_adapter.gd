extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _store: Node

func before() -> void:
    _store = load("res://Game.Godot/Adapters/DataStoreAdapter.cs").new()
    add_child(auto_free(_store))

func test_save_load_delete_user_path() -> void:
    var key := "selfcheck/test-" + str(Time.get_unix_time_from_system())
    var payload := "{\"ok\":true}"
    _store.SaveSync(key, payload)
    var loaded = _store.LoadSync(key)
    assert_str(loaded).is_equal(payload)
    _store.DeleteSync(key)
    var after_value = _store.LoadSync(key)
    # Godot C# interop: C# null string can appear as empty in GDScript
    assert_str(str(after_value)).is_empty()

func test_make_safe_key_with_invalid_chars() -> void:
    var key := "a/b?c:*|<>"
    var payload := "X"
    _store.SaveSync(key, payload)
    var loaded = _store.LoadSync(key)
    assert_str(loaded).is_equal(payload)
    _store.DeleteSync(key)

