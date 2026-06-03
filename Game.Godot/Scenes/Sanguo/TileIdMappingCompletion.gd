extends RefCounted

func complete_tile_id_mapping(map_definition: Dictionary) -> Dictionary:
	var tiles: Array = map_definition.get("tiles", [])
	if tiles.is_empty():
		return {
			"completed": false,
			"mapping": {},
			"visible_ids": []
		}

	var mapping := {}
	var visible_ids: Array = []
	for tile in tiles:
		if typeof(tile) != TYPE_DICTIONARY:
			return {
				"completed": false,
				"mapping": {},
				"visible_ids": []
			}
		var tile_dict: Dictionary = tile
		var tile_id := str(tile_dict.get("id", tile_dict.get("tileId", ""))).strip_edges()
		if tile_id.is_empty():
			return {
				"completed": false,
				"mapping": {},
				"visible_ids": []
			}
		mapping[tile_id] = true
		visible_ids.append(tile_id)

	return {
		"completed": true,
		"mapping": mapping,
		"visible_ids": visible_ids
	}
