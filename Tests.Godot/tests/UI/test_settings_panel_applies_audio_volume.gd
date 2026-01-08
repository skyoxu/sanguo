extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CFG_FILENAME := "settings.cfg"

func _clear_config() -> void:
	var dir := DirAccess.open("user://")
	if dir != null and dir.file_exists(CFG_FILENAME):
		dir.remove(CFG_FILENAME)

# ACC:T29.4
func test_settings_panel_volume_slider_applies_master_bus_volume() -> void:
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
	AudioServer.set_bus_volume_db(bus, -24.0)
	var before_db := AudioServer.get_bus_volume_db(bus)

	var panel = packed.instantiate()
	add_child(auto_free(panel))
	await get_tree().process_frame

	var slider := panel.get_node("VBox/VolRow/VolSlider") as Range
	assert_bool(slider != null).is_true()
	if slider == null:
		AudioServer.set_bus_volume_db(bus, original_db)
		return

	var save_btn := panel.get_node("VBox/Buttons/SaveBtn")
	var load_btn := panel.get_node("VBox/Buttons/LoadBtn")
	assert_bool(save_btn != null and load_btn != null).is_true()
	if save_btn == null or load_btn == null:
		AudioServer.set_bus_volume_db(bus, original_db)
		return

	slider.value = 0.65
	await get_tree().process_frame
	save_btn.emit_signal("pressed")
	await get_tree().process_frame

	slider.value = 0.1
	await get_tree().process_frame
	load_btn.emit_signal("pressed")
	await get_tree().process_frame

	var after_db := AudioServer.get_bus_volume_db(bus)
	var expected_db := linear_to_db(float(slider.value))
	assert_bool(abs(after_db - expected_db) < 0.75).is_true()
	assert_bool(abs(after_db - before_db) > 0.001).is_true()

	# Restore previous state to avoid test interference
	AudioServer.set_bus_volume_db(bus, original_db)
