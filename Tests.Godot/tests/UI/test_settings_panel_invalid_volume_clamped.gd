extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CFG_FILENAME := "settings.cfg"
const CFG_PATH := "user://settings.cfg"

func _clear_config() -> void:
	var dir := DirAccess.open("user://")
	if dir != null and dir.file_exists(CFG_FILENAME):
		dir.remove(CFG_FILENAME)

func _sanitize_volume_linear(raw_value: float, min_value: float, max_value: float) -> float:
	return clampf(raw_value, min_value, max_value)

func test_volume_sanitize_helper_clamps_out_of_range() -> void:
	assert_float(_sanitize_volume_linear(-10.0, 0.0, 1.0)).is_equal(0.0)
	assert_float(_sanitize_volume_linear(10.0, 0.0, 1.0)).is_equal(1.0)
	assert_float(_sanitize_volume_linear(0.25, 0.0, 1.0)).is_equal(0.25)

# ACC:T29.7
# Acceptance intent: invalid volume should not crash and should end up clamped/fallback to a valid range.
func test_settings_panel_invalid_volume_is_clamped_and_loadable() -> void:
	_clear_config()

	var packed := load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn") as PackedScene
	assert_bool(packed != null).is_true()
	if packed == null:
		return

	var bus := AudioServer.get_bus_index("Master")
	assert_bool(bus >= 0).is_true()
	if bus < 0:
		return

	var original_db := AudioServer.get_bus_volume_db(bus)
	AudioServer.set_bus_volume_db(bus, -30.0)
	var before_db := AudioServer.get_bus_volume_db(bus)

	# Write an out-of-range value directly into ConfigFile (UI slider cannot exceed max).
	var cfg := ConfigFile.new()
	cfg.set_value("settings", "vol", 999.0)
	cfg.set_value("settings", "gfx", "medium")
	cfg.set_value("settings", "lang", "en")
	cfg.set_value("settings", "resolution", "")
	cfg.set_value("settings", "window_mode", "windowed")
	var err := cfg.save(CFG_PATH)
	assert_int(err).is_equal(OK)

	var panel := packed.instantiate()
	add_child(auto_free(panel))
	await get_tree().process_frame

	var slider := panel.get_node_or_null("VBox/VolRow/VolSlider") as Range
	assert_bool(slider != null).is_true()
	if slider == null:
		AudioServer.set_bus_volume_db(bus, original_db)
		return

	var load_btn := panel.get_node_or_null("VBox/Buttons/LoadBtn")
	assert_bool(load_btn != null).is_true()
	if load_btn == null:
		AudioServer.set_bus_volume_db(bus, original_db)
		return

	# Load invalid value and ensure runtime/UI clamps it.
	load_btn.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(abs(float(slider.value) - float(slider.max_value)) < 0.0001).is_true()

	var after_db := AudioServer.get_bus_volume_db(bus)
	var expected_db := linear_to_db(float(slider.value))
	assert_bool(abs(after_db - expected_db) < 0.75).is_true()
	assert_bool(abs(after_db - before_db) > 0.001).is_true()

	# Restore previous state to avoid test interference.
	AudioServer.set_bus_volume_db(bus, original_db)
