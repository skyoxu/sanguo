extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"
const CORE_TURN_STARTED := "core.sanguo.game.turn.started"

func _ensure_event_bus() -> Node:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "EventBus"
	get_tree().get_root().add_child(bus)
	return bus

var _events: Array = []

func _on_domain_event_emitted(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	_events.append({"type": str(type)})

func _has_event(type_name: String) -> bool:
	for e in _events:
		if str(e.get("type", "")) == type_name:
			return true
	return false

# ACC:T27.4
func test_hud_sfx_does_not_stop_music() -> void:
	var bus := _ensure_event_bus()
	assert_bool(bus.is_inside_tree()).is_true()
	bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
	_events = []

	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	assert_bool(main.is_inside_tree()).is_true()

	bus.call("PublishSimple", UI_MENU_START, "gdunit", "{}")
	for _i in range(0, 180):
		await get_tree().process_frame
		if _has_event(CORE_TURN_STARTED):
			break
	assert_bool(_has_event(CORE_TURN_STARTED)).is_true()

	var music: AudioStreamPlayer = main.get_node_or_null("Audio/MusicPlayer")
	var sfx: AudioStreamPlayer = main.get_node_or_null("Audio/SfxPlayer")
	assert_object(music).is_not_null()
	assert_object(sfx).is_not_null()

	assert_object(music.stream).is_not_null()
	var music_was_playing := music.playing
	if music_was_playing:
		var music_playback_before := music.get_stream_playback()
		assert_object(music_playback_before).is_not_null()

	sfx.stop()
	sfx.stream = null
	await get_tree().process_frame
	assert_bool(sfx.playing).is_false()

	var hud := main.get_node_or_null("SplitRoot/TopArea/HudLayer/HUD")
	assert_object(hud).is_not_null()
	var dice: Button = hud.get_node_or_null("TopBar/TopStack/HBox/DiceButton")
	assert_object(dice).is_not_null()

	dice.emit_signal("pressed")
	for _i in range(0, 10):
		await get_tree().process_frame
		if sfx.playing:
			break

	# ACC:T27.4
	assert_object(sfx.stream).is_not_null()
	assert_bool(sfx.playing).is_true()
	assert_bool(music.playing).is_equal(music_was_playing)
	if music_was_playing:
		assert_object(music.get_stream_playback()).is_not_null()


func after() -> void:
	var bus := get_node_or_null("/root/EventBus")
	if bus != null and is_instance_valid(bus):
		bus.queue_free()
	await get_tree().process_frame
