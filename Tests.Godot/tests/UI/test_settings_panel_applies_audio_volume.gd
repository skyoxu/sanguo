extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T27.2
func test_settings_panel_volume_slider_applies_master_bus_volume() -> void:
	var packed := load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn") as PackedScene
	if packed == null:
		push_warning("SKIP: SettingsPanel.tscn not found")
		return

	var bus := AudioServer.get_bus_index("Master")
	if bus < 0:
		push_warning("SKIP: Master audio bus not found")
		return

	var before_db := AudioServer.get_bus_volume_db(bus)

	var panel = packed.instantiate()
	add_child(auto_free(panel))
	await get_tree().process_frame

	var slider := panel.get_node("VBox/VolRow/VolSlider")
	slider.value = 0.7
	await get_tree().process_frame

	var after_db := AudioServer.get_bus_volume_db(bus)
	assert_bool(abs(after_db - before_db) > 0.001).is_true()

	# Restore previous state to avoid test interference
	AudioServer.set_bus_volume_db(bus, before_db)
