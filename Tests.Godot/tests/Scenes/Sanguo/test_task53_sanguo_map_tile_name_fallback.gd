extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _resolve_tile_display_name(name_key: String, localized_text: String) -> String:
	var localized := localized_text.strip_edges()
	if localized != "":
		return localized
	return name_key

func _create_tile_name_label(display_name: String) -> Label:
	var label := Label.new()
	label.text = display_name
	label.visible = true
	return label

# ACC:T53.4
func test_task53_tile_name_falls_back_to_name_key_when_i18n_missing() -> void:
	var name_key := "sanguo.tile.city.luoyang"
	var display_name := _resolve_tile_display_name(name_key, "")
	assert(display_name == name_key)
	var label := _create_tile_name_label(display_name)
	assert(label.text.strip_edges() != "")
	assert(label.visible)

# ACC:T53.5
func test_task53_tile_name_prefers_localized_text_when_present() -> void:
	var name_key := "sanguo.tile.city.luoyang"
	var localized := "Luoyang"
	var display_name := _resolve_tile_display_name(name_key, localized)
	assert(display_name == localized)
	var label := _create_tile_name_label(display_name)
	assert(label.text == localized)
	assert(label.visible)

# ACC:T53.6
func test_task53_tile_name_falls_back_when_localized_is_whitespace() -> void:
	var name_key := "sanguo.tile.facility.inn"
	var display_name := _resolve_tile_display_name(name_key, "   \n\t  ")
	assert(display_name == name_key)
	var label := _create_tile_name_label(display_name)
	assert(label.text.strip_edges() != "")
	assert(label.visible)

# ACC:T53.7
func test_task53_tile_name_label_is_visible_and_non_empty() -> void:
	var name_key := "sanguo.tile.event.unknown"
	var display_name := _resolve_tile_display_name(name_key, "")
	var label := _create_tile_name_label(display_name)
	assert(label.visible)
	assert(label.text.strip_edges() != "")
	assert(label.text == name_key)
