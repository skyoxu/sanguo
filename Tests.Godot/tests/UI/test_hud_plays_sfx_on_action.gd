extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"

func _ensure_event_bus() -> Node:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(bus))
	return bus

# ACC:T27.3
func test_hud_plays_sfx_on_action_smoke() -> void:
	var bus := _ensure_event_bus()
	assert_bool(bus.is_inside_tree()).is_true()

	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	assert_bool(main.is_inside_tree()).is_true()

	bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
	await get_tree().process_frame

	var sfx: AudioStreamPlayer = main.get_node_or_null("Audio/SfxPlayer")
	assert_object(sfx).is_not_null()

	for _i in range(0, 10):
		await get_tree().process_frame
		if sfx.get_stream_playback() != null:
			break

	# ACC:T27.3
	assert_object(sfx.stream).is_not_null()
	assert_object(sfx.get_stream_playback()).is_not_null()
