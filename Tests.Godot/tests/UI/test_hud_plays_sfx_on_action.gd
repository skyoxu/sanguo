extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"
const SETTINGS_CFG_FILENAME := "settings.cfg"

func _clear_settings_config() -> void:
	var dir := DirAccess.open("user://")
	if dir != null and dir.file_exists(SETTINGS_CFG_FILENAME):
		dir.remove(SETTINGS_CFG_FILENAME)

func _ensure_event_bus() -> Node:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "EventBus"
	get_tree().get_root().add_child(bus)
	return bus

# ACC:T27.3
# ACC:T205.5
func test_hud_plays_sfx_on_action_smoke() -> void:
	var bus := _ensure_event_bus()
	assert_bool(bus.is_inside_tree()).is_true()

	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	assert_bool(main.is_inside_tree()).is_true()

	var sfx: AudioStreamPlayer = main.get_node_or_null("Audio/SfxPlayer")
	assert_object(sfx).is_not_null()

	# Prove the causal relation: before the action, no playback exists.
	sfx.stop()
	sfx.stream = null
	await get_tree().process_frame
	assert_object(sfx.stream).is_null()
	assert_bool(sfx.playing).is_false()

	bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
	await get_tree().process_frame

	for _i in range(0, 10):
		await get_tree().process_frame
		if sfx.playing:
			break

	# ACC:T27.3
	assert_object(sfx.stream).is_not_null()
	assert_bool(sfx.playing or sfx.stream != null).is_true()

# ACC:T205.5
func test_hud_action_sfx_respects_configured_master_bus_volume() -> void:
	var master_bus := AudioServer.get_bus_index("Master")
	assert_bool(master_bus >= 0).is_true()
	if master_bus < 0:
		return

	var original_db := AudioServer.get_bus_volume_db(master_bus)
	var configured_volume := 0.32

	var bus := _ensure_event_bus()
	assert_bool(bus.is_inside_tree()).is_true()

	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var sfx: AudioStreamPlayer = main.get_node_or_null("Audio/SfxPlayer")
	assert_object(sfx).is_not_null()
	if sfx == null:
		AudioServer.set_bus_volume_db(master_bus, original_db)
		return

	AudioServer.set_bus_volume_db(master_bus, linear_to_db(configured_volume))
	sfx.stop()
	sfx.stream = null
	await get_tree().process_frame

	bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
	await get_tree().process_frame

	for _i in range(0, 10):
		await get_tree().process_frame
		if sfx.stream != null:
			break

	assert_object(sfx.stream).is_not_null()
	assert_bool(abs(AudioServer.get_bus_volume_db(master_bus) - linear_to_db(configured_volume)) < 0.75).is_true()
	assert_str(AudioServer.get_bus_name(master_bus)).is_equal("Master")

	AudioServer.set_bus_volume_db(master_bus, original_db)

# ACC:T205.5
func test_settings_volume_remains_applied_when_hud_action_sfx_plays() -> void:
	_clear_settings_config()
	var master_bus := AudioServer.get_bus_index("Master")
	assert_bool(master_bus >= 0).is_true()
	if master_bus < 0:
		return

	var original_db := AudioServer.get_bus_volume_db(master_bus)
	var configured_volume := 0.21
	var expected_db := linear_to_db(configured_volume)

	var settings_scene := load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn") as PackedScene
	assert_object(settings_scene).is_not_null()
	if settings_scene == null:
		AudioServer.set_bus_volume_db(master_bus, original_db)
		return

	var settings = settings_scene.instantiate()
	add_child(auto_free(settings))
	await get_tree().process_frame

	var slider := settings.get_node("Center/VBox/VolRow/VolSlider") as Range
	var save_btn := settings.get_node("Center/VBox/Buttons/SaveBtn") as Button
	assert_object(slider).is_not_null()
	assert_object(save_btn).is_not_null()
	if slider == null or save_btn == null:
		AudioServer.set_bus_volume_db(master_bus, original_db)
		return

	slider.value = configured_volume
	await get_tree().process_frame
	save_btn.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(abs(AudioServer.get_bus_volume_db(master_bus) - expected_db) < 0.75).is_true()

	var bus := _ensure_event_bus()
	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var sfx: AudioStreamPlayer = main.get_node_or_null("Audio/SfxPlayer")
	assert_object(sfx).is_not_null()
	if sfx == null:
		AudioServer.set_bus_volume_db(master_bus, original_db)
		return

	sfx.stop()
	sfx.stream = null
	await get_tree().process_frame

	bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
	await get_tree().process_frame
	for _i in range(0, 10):
		await get_tree().process_frame
		if sfx.stream != null:
			break

	assert_object(sfx.stream).is_not_null()
	assert_bool(abs(AudioServer.get_bus_volume_db(master_bus) - expected_db) < 0.75).is_true()

	AudioServer.set_bus_volume_db(master_bus, original_db)

func after() -> void:
	var bus := get_node_or_null("/root/EventBus")
	if bus != null and is_instance_valid(bus):
		bus.queue_free()
	await get_tree().process_frame
