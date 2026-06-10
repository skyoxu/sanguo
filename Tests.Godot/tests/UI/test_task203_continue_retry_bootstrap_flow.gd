extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

const EVT_MENU_START := "ui.menu.start"
const EVT_MENU_LOAD := "ui.menu.load"
const EVT_HUD_LOAD := "ui.hud.load"
const EVT_MENU_START_FAILED := "ui.menu.start.failed"
const EVT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVT_GAME_SAVED := "core.sanguo.game.saved"
const EVT_GAME_LOADED := "core.sanguo.game.loaded"

const PATH_MAIN_SCENE := "res://Game.Godot/Scenes/Main.tscn"
const PATH_FAILING_LOADER := "res://Game.Godot/Adapters/TestFailingResourceLoader.cs"
const PATH_DEFAULT_LOADER := "res://Game.Godot/Adapters/ResourceLoaderAdapter.cs"

var _bus: Node
var _events: Array[Dictionary] = []

func before() -> void:
	_events = []
	OS.set_environment("AUDIT_LOG_ROOT", ProjectSettings.globalize_path("user://logs/ci"))
	_reset_named_root_node("EventBus")
	_reset_named_root_node("CompositionRoot")

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func _on_domain_event_emitted(type, source, data_json, id, spec, ct, ts) -> void:
	_events.append({
		"type": str(type),
		"source": str(source),
		"data_json": str(data_json),
		"id": str(id),
		"spec": str(spec),
		"ct": str(ct),
		"ts": str(ts),
	})

func _reset_named_root_node(node_name: String) -> void:
	var node := get_node_or_null("/root/" + node_name)
	if node != null:
		var parent := node.get_parent()
		if parent != null:
			parent.remove_child(node)
		node.free()

func _set_resource_loader_port(loader_script_path: String) -> void:
	_reset_named_root_node("CompositionRoot")
	var root := Node.new()
	root.name = "CompositionRoot"
	get_tree().get_root().add_child(root)
	var loader = load(loader_script_path).new()
	loader.name = "ResourceLoaderPort"
	root.add_child(loader)

func _create_main() -> Node:
	var main = preload(PATH_MAIN_SCENE).instantiate()
	add_child(auto_free(main))
	return main

func _event_types() -> Array[String]:
	var types: Array[String] = []
	for evt in _events:
		types.append(str(evt.get("type", "")))
	return types

func _last_event(event_type: String) -> Dictionary:
	for i in range(_events.size() - 1, -1, -1):
		var evt := _events[i]
		if str(evt.get("type", "")) == event_type:
			return evt
	return {}

func _wait_for_event(event_type: String, max_frames: int = 240) -> Dictionary:
	for _i in range(max_frames):
		var evt := _last_event(event_type)
		if not evt.is_empty():
			return evt
		await get_tree().process_frame
	return {}

func _count_events(event_type: String) -> int:
	var count := 0
	for evt in _events:
		if str(evt.get("type", "")) == event_type:
			count += 1
	return count

func _visible_button_text(button: Button) -> String:
	return str(button.text).strip_edges().to_lower()

func _publish_test_event(event_type: String, payload_json: String = "{}") -> void:
	_bus.emit_signal("DomainEventEmitted", event_type, "gdunit", payload_json, "rid-" + event_type, "1.0.0", "application/json", Time.get_datetime_string_from_system())

# acceptance: ACC:T203.1
# acceptance: ACC:T203.4
# ACC:T206.1
func test_task203_start_shows_platform_validation_state_before_gameplay() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var btn_play := menu.get_node_or_null("MenuRow/MenuBox/BtnPlay") as Button
	var btn_start := menu.get_node_or_null("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart") as Button
	var status := menu.get_node_or_null("StatusLabel") as Label
	assert_object(btn_play).is_not_null()
	assert_object(btn_start).is_not_null()
	assert_object(status).is_not_null()
	if btn_play == null or btn_start == null or status == null:
		return

	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	btn_start.emit_signal("pressed")

	assert_bool(status.visible).is_true()
	assert_str(status.text.to_lower()).contains("validation")
	assert_bool(_event_types().has(EVT_MENU_START)).is_true()

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()

# acceptance: ACC:T203.2
# acceptance: ACC:T203.3
# acceptance: ACC:T203.5
# acceptance: ACC:T203.8
# acceptance: ACC:T203.9
# ACC:T206.8
func test_task203_continue_is_visible_only_after_saved_state_and_does_not_bootstrap_new_run() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var continue_button := menu.get_node_or_null("MenuRow/MenuBox/BtnLoad") as Button
	assert_object(continue_button).is_not_null()
	if continue_button == null:
		return

	assert_bool(continue_button.visible).is_true()

	_publish_test_event(EVT_GAME_SAVED, "{\"SaveSlotId\":\"quick\",\"GameId\":\"g-existing\"}")
	await get_tree().process_frame
	_events.clear()
	_publish_test_event("ui.menu.return", "{\"reason\":\"task203_continue\"}")
	for _i in range(5):
		await get_tree().process_frame

	assert_bool(menu.visible).is_true()
	assert_bool(continue_button.visible).is_true()
	assert_bool(continue_button.disabled).is_false()
	assert_bool(_visible_button_text(continue_button).contains("continue")).is_true()

	continue_button.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(_event_types().has(EVT_MENU_LOAD)).is_true()
	assert_bool(_event_types().has(EVT_HUD_LOAD)).is_true()
	assert_bool(_event_types().has(EVT_MENU_START)).is_false()

	_publish_test_event(EVT_GAME_LOADED, "{\"SaveSlotId\":\"quick\",\"GameId\":\"g-existing\"}")
	await get_tree().process_frame
	assert_bool(menu.visible).is_false()

# acceptance: ACC:T203.6 ACC:T203.7 ACC:T203.10 ACC:T203.11
# acceptance: ACC:T203.12 ACC:T203.13 ACC:T203.14 ACC:T203.15
# ACC:T206.4
# ACC:T206.9
func test_task203_blocked_validation_shows_retry_and_retry_replaces_failed_result() -> void:
	_set_resource_loader_port(PATH_FAILING_LOADER)

	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var btn_start := menu.get_node_or_null("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart") as Button
	var status := menu.get_node_or_null("StatusLabel") as Label
	assert_object(btn_start).is_not_null()
	assert_object(status).is_not_null()
	if btn_start == null or status == null:
		return

	var first_try_ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(first_try_ok).is_true()
	if not first_try_ok:
		return

	var failed_evt := await _wait_for_event(EVT_MENU_START_FAILED, 360)
	assert_bool(not failed_evt.is_empty()).is_true()
	assert_bool(menu.visible).is_true()
	assert_bool(status.visible).is_true()
	assert_str(status.text.to_lower()).contains("blocked")
	assert_str(status.text.to_lower()).contains("validation")
	assert_bool(_visible_button_text(btn_start).contains("retry")).is_true()
	assert_int(_count_events(EVT_TURN_STARTED)).is_equal(0)

	_set_resource_loader_port(PATH_DEFAULT_LOADER)
	await get_tree().process_frame

	_events.clear()
	btn_start.emit_signal("pressed")
	assert_bool(status.visible).is_true()
	assert_str(status.text.to_lower()).contains("validation")
	assert_str(status.text.to_lower()).not_contains("blocked")

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()
	assert_bool(menu.visible).is_false()
	assert_int(_count_events(EVT_MENU_START_FAILED)).is_equal(0)
