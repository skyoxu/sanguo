extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _make_store(name: String = "Task190DataStore") -> Node:
	var store := preload("res://Game.Godot/Adapters/DataStoreAdapter.cs").new()
	store.name = name
	add_child(auto_free(store))
	return store

func _safe_key(base_key: String) -> String:
	return "%s_%s" % [base_key, Time.get_unix_time_from_system()]

func test_data_store_save_load_delete_roundtrip() -> void:
	var store := _make_store()
	var key := _safe_key("task190_roundtrip")
	var payload := "{\"gold\":123,\"version\":1}"

	store.call("SaveSync", key, payload)
	var loaded = store.call("LoadSync", key)
	assert_str(str(loaded)).is_equal(payload)

	store.call("DeleteSync", key)
	var deleted = store.call("LoadSync", key)
	var deleted_text := "" if deleted == null else str(deleted)
	assert_bool(deleted == null or deleted_text == "").is_true()

# ACC:T190.8
func test_data_store_load_missing_key_returns_null() -> void:
	var store := _make_store()
	var missing_key := _safe_key("task190_missing")
	store.call("DeleteSync", missing_key)
	var loaded_missing = store.call("LoadSync", missing_key)
	var loaded_missing_text := "" if loaded_missing == null else str(loaded_missing)
	assert_bool(loaded_missing == null or loaded_missing_text == "").is_true()
