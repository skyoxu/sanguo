extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CANDIDATE_RUNTIME_BOUNDARIES := [
	"res://Game.Godot/Scenes/Sanguo/TileIdMappingCompletion.gd",
	"res://Game.Godot/Adapters/Sanguo/TileIdMappingAdapter.gd",
	"res://Scenes/Sanguo/TileIdMappingCompletion.gd",
	"res://Scripts/Sanguo/TileIdMappingCompletion.gd"
]

const VALID_MAP_DEFINITION := {
	"map_id": "task193_valid_map",
	"tiles": [
		{"id": "capital_luoyang", "name": "Luoyang", "kind": "capital"},
		{"id": "city_changan", "name": "Changan", "kind": "city"},
		{"id": "pass_hulao", "name": "Hulao Pass", "kind": "pass"}
	]
}

const EMPTY_MAP_DEFINITION := {
	"map_id": "task193_empty_map",
	"tiles": []
}

var _boundary: Object = null

func before_test() -> void:
	_boundary = _create_runtime_boundary()

func after_test() -> void:
	if _boundary is Node and is_instance_valid(_boundary):
		_boundary.queue_free()
	_boundary = null

func _create_runtime_boundary() -> Object:
	for path in CANDIDATE_RUNTIME_BOUNDARIES:
		if FileAccess.file_exists(path):
			var script := load(path)
			if script != null:
				var instance: Object = script.new()
				if instance is Node:
					add_child(instance)
				return instance
	return null

func _exercise_mapping_completion(map_definition: Dictionary) -> Dictionary:
	assert_that(_boundary).is_not_null()
	if _boundary == null:
		return {"completed": false, "mapping": {}, "visible_ids": []}

	if _boundary.has_method("complete_tile_id_mapping"):
		return _normalize_result(_boundary.call("complete_tile_id_mapping", map_definition))
	if _boundary.has_method("build_tile_id_mapping"):
		return _normalize_result(_boundary.call("build_tile_id_mapping", map_definition))
	if _boundary.has_method("map_tile_ids"):
		return _normalize_result(_boundary.call("map_tile_ids", map_definition))
	if _boundary.has_method("load_map_definition") and _boundary.has_method("get_tile_id_mapping_state"):
		_boundary.call("load_map_definition", map_definition)
		return _normalize_result(_boundary.call("get_tile_id_mapping_state"))

	assert_that(_boundary.has_method("complete_tile_id_mapping")).is_true()
	return {"completed": false, "mapping": {}, "visible_ids": []}

func _normalize_result(raw_result: Variant) -> Dictionary:
	if raw_result is Dictionary:
		var mapping: Dictionary = raw_result.get("mapping", raw_result.get("tile_id_mapping", {}))
		var visible_ids: Array = raw_result.get("visible_ids", raw_result.get("tile_ids", mapping.keys()))
		return {
			"completed": bool(raw_result.get("completed", raw_result.get("success", false))),
			"mapping": mapping,
			"visible_ids": visible_ids
		}
	if raw_result is Array:
		var generated_mapping := {}
		for tile_id in raw_result:
			generated_mapping[str(tile_id)] = true
		return {"completed": raw_result.size() > 0, "mapping": generated_mapping, "visible_ids": raw_result}
	return {"completed": false, "mapping": {}, "visible_ids": []}

# acceptance: ACC:T193.4
# Valid map definitions must complete tile-id mapping at the runtime boundary.
func test_valid_map_definition_completes_tile_id_mapping() -> void:
	var result := _exercise_mapping_completion(VALID_MAP_DEFINITION)

	assert_that(result["completed"]).is_true()
	assert_that(result["mapping"].has("capital_luoyang")).is_true()
	assert_that(result["mapping"].has("city_changan")).is_true()
	assert_that(result["mapping"].has("pass_hulao")).is_true()

# acceptance: ACC:T193.5
# Empty tile arrays must not be reported as completed mapping success.
func test_empty_tiles_array_refuses_completion_success() -> void:
	var result := _exercise_mapping_completion(EMPTY_MAP_DEFINITION)

	assert_that(result["completed"]).is_false()
	assert_that(result["mapping"].is_empty()).is_true()

# acceptance: ACC:T193.4
# Player-visible ids must be exposed after a valid mapping pass.
func test_player_visible_tile_ids_match_valid_map_definition() -> void:
	var result := _exercise_mapping_completion(VALID_MAP_DEFINITION)

	assert_that(result["visible_ids"]).contains("capital_luoyang")
	assert_that(result["visible_ids"]).contains("city_changan")
	assert_that(result["visible_ids"]).contains("pass_hulao")

# acceptance: ACC:T193.4
# The test must exercise a Godot-side scene or adapter runtime boundary.
func test_runtime_boundary_is_node_or_adapter_object() -> void:
	assert_that(_boundary).is_not_null()
	assert_that(_boundary is Node or _boundary is RefCounted).is_true()

# acceptance: ACC:T193.4
# Runtime wiring must expose a mapping completion behavior, not only static data.
func test_runtime_boundary_exposes_mapping_completion_behavior() -> void:
	assert_that(_boundary).is_not_null()
	var exposes_behavior := _boundary != null and (
		_boundary.has_method("complete_tile_id_mapping")
		or _boundary.has_method("build_tile_id_mapping")
		or _boundary.has_method("map_tile_ids")
		or (_boundary.has_method("load_map_definition") and _boundary.has_method("get_tile_id_mapping_state"))
	)

	assert_that(exposes_behavior).is_true()
