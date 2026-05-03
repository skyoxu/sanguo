extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

const EVT_MENU_START := "ui.menu.start"
const EVT_MENU_LOAD := "ui.menu.load"
const EVT_HUD_LOAD := "ui.hud.load"
const EVT_MENU_START_FAILED := "ui.menu.start.failed"
const EVT_GAME_STARTED := "core.sanguo.game.started"
const EVT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVT_GAME_SAVED := "core.sanguo.game.saved"
const EVT_GAME_LOADED := "core.sanguo.game.loaded"

const PATH_MAIN_SCENE := "res://Game.Godot/Scenes/Main.tscn"
const PATH_FAILING_LOADER := "res://Game.Godot/Adapters/TestFailingResourceLoader.cs"
const PATH_DEFAULT_LOADER := "res://Game.Godot/Adapters/ResourceLoaderAdapter.cs"

const PATH_HUD := "SplitRoot/TopArea/HudLayer/HUD"
const PATH_BTN_SETTINGS := "TopBar/TopStack/HBox/GameSettingsButton"
const PATH_BTN_SAVE := "SettingsMenu/Center/Panel/VBox/BtnSave"
const PATH_BTN_LOAD := "SettingsMenu/Center/Panel/VBox/BtnLoad"

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
		node.name = "%s__old__%s" % [node_name, str(Time.get_ticks_msec())]
		node.queue_free()

func _set_resource_loader_port(loader_script_path: String) -> void:
	_reset_named_root_node("CompositionRoot")
	var root := Node.new()
	root.name = "CompositionRoot"
	get_tree().get_root().add_child(auto_free(root))
	var loader = load(loader_script_path).new()
	loader.name = "ResourceLoaderPort"
	root.add_child(auto_free(loader))

func _event_types() -> Array[String]:
	var types: Array[String] = []
	for e in _events:
		types.append(str(e.get("type", "")))
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

func _join_strings(values: Array) -> String:
	var out := ""
	for i in range(values.size()):
		if i > 0:
			out += " "
		out += str(values[i])
	return out

func _read_res_text(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return ""
	return file.get_as_text(true)

func _parse_json_dict(json_text: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(json_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed as Dictionary

func _create_main() -> Node:
	var main = preload(PATH_MAIN_SCENE).instantiate()
	add_child(auto_free(main))
	return main

func _repo_file_text(relative_repo_path: String) -> String:
	var tests_root := ProjectSettings.globalize_path("res://")
	var repo_root := tests_root.path_join("..").simplify_path()
	var abs_path := repo_root.path_join(relative_repo_path)
	if not FileAccess.file_exists(abs_path):
		return ""
	var file := FileAccess.open(abs_path, FileAccess.READ)
	if file == null:
		return ""
	return file.get_as_text(true)

func _task176_from(relative_repo_path: String) -> Dictionary:
	var raw := _repo_file_text(relative_repo_path)
	if raw.is_empty():
		raw = _read_res_text("res://" + relative_repo_path)
	assert_str(raw).is_not_empty()
	if raw.is_empty():
		return {}
	var parsed: Variant = JSON.parse_string(raw)
	assert_bool(typeof(parsed) == TYPE_ARRAY).is_true()
	if typeof(parsed) != TYPE_ARRAY:
		return {}
	for item in parsed:
		if typeof(item) == TYPE_DICTIONARY and str(item.get("taskmaster_id", "")) == "176":
			return item as Dictionary
	return {}

# ACC:T176.1
func test_task176_launch_and_enter_run_have_real_mainmenu_wiring() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var btn_play := menu.get_node_or_null("MenuRow/MenuBox/BtnPlay")
	var btn_start := menu.get_node_or_null("ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart")
	assert_object(btn_play).is_not_null()
	assert_object(btn_start).is_not_null()
	if btn_play == null or btn_start == null:
		return

	var ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(ok).is_true()
	if not ok:
		return

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()
	assert_bool(_event_types().has(EVT_MENU_START)).is_true()
	assert_bool(menu.visible).is_false()

# ACC:T176.2
func test_task176_continue_request_without_save_header_stays_in_gate_surface() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var btn_load = menu.get_node_or_null("MenuRow/MenuBox/BtnLoad")
	var load_panel = menu.get_node_or_null("LoadPanel")
	assert_object(btn_load).is_not_null()
	assert_object(load_panel).is_not_null()
	if btn_load == null or load_panel == null:
		return

	btn_load.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(_event_types().has(EVT_MENU_LOAD)).is_true()
	assert_bool(_event_types().has(EVT_HUD_LOAD)).is_true()
	assert_bool((load_panel as Control).visible).is_true()

	for _i in range(60):
		await get_tree().process_frame
	assert_bool(_event_types().has(EVT_GAME_LOADED)).is_false()
	assert_bool(menu.visible).is_true()

func test_task176_continue_request_with_saved_header_enters_loaded_state() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(ok).is_true()
	if not ok:
		return

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()
	if turn_started.is_empty():
		return

	var hud := main.get_node_or_null(PATH_HUD)
	assert_object(hud).is_not_null()
	if hud == null:
		return

	var btn_settings := hud.get_node_or_null(PATH_BTN_SETTINGS)
	var btn_save := hud.get_node_or_null(PATH_BTN_SAVE)
	assert_object(btn_settings).is_not_null()
	assert_object(btn_save).is_not_null()
	if btn_settings == null or btn_save == null:
		return

	btn_settings.emit_signal("pressed")
	for _i in range(30):
		await get_tree().process_frame
	btn_save.emit_signal("pressed")
	var saved_evt := await _wait_for_event(EVT_GAME_SAVED, 900)
	assert_bool(not saved_evt.is_empty()).is_true()
	if saved_evt.is_empty():
		return

	_events.clear()
	var ui_return_payload := "{\"reason\":\"test_continue_gate\"}"
	_bus.emit_signal("DomainEventEmitted", "ui.menu.return", "ui", ui_return_payload, "rid-return", "1.0.0", "application/json", Time.get_datetime_string_from_system())
	for _i in range(5):
		await get_tree().process_frame
	assert_bool(menu.visible).is_true()

	var btn_load = menu.get_node_or_null("MenuRow/MenuBox/BtnLoad")
	assert_object(btn_load).is_not_null()
	if btn_load == null:
		return

	btn_load.emit_signal("pressed")
	var loaded_evt := await _wait_for_event(EVT_GAME_LOADED, 900)
	assert_bool(not loaded_evt.is_empty()).is_true()
	if loaded_evt.is_empty():
		return

	assert_bool(_event_types().has(EVT_MENU_LOAD)).is_true()
	assert_bool(_event_types().has(EVT_HUD_LOAD)).is_true()
	assert_bool(menu.visible).is_false()

# ACC:T176.3
func test_task176_startup_failure_requires_retry_before_run_can_start() -> void:
	_set_resource_loader_port(PATH_FAILING_LOADER)

	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var first_try_ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(first_try_ok).is_true()
	if not first_try_ok:
		return

	var failed_evt := await _wait_for_event(EVT_MENU_START_FAILED, 240)
	assert_bool(not failed_evt.is_empty()).is_true()
	var failed_turn_count := _count_events(EVT_TURN_STARTED)
	for _i in range(30):
		await get_tree().process_frame
	assert_int(_count_events(EVT_TURN_STARTED)).is_equal(failed_turn_count)
	assert_bool(menu.visible).is_true()

	var status = menu.get_node_or_null("StatusLabel")
	assert_object(status).is_not_null()
	if status != null:
		assert_bool((status as Label).visible).is_true()
		assert_str((status as Label).text).is_not_empty()

	_set_resource_loader_port(PATH_DEFAULT_LOADER)
	await get_tree().process_frame

	_events.clear()
	var second_try_ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(second_try_ok).is_true()
	if not second_try_ok:
		return

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()

# ACC:T176.4
func test_task176_save_and_load_events_keep_reproducible_run_context_fields() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(ok).is_true()
	if not ok:
		return

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()

	var hud := main.get_node_or_null(PATH_HUD)
	assert_object(hud).is_not_null()
	if hud == null:
		return

	var btn_settings := hud.get_node_or_null(PATH_BTN_SETTINGS)
	var btn_save := hud.get_node_or_null(PATH_BTN_SAVE)
	var btn_load := hud.get_node_or_null(PATH_BTN_LOAD)
	assert_object(btn_settings).is_not_null()
	assert_object(btn_save).is_not_null()
	assert_object(btn_load).is_not_null()
	if btn_settings == null or btn_save == null or btn_load == null:
		return

	_events.clear()
	btn_settings.emit_signal("pressed")
	for _i in range(30):
		await get_tree().process_frame
	var save_source_count := _count_events("ui.hud.save")
	btn_save.emit_signal("pressed")
	var save_ui_evt := await _wait_for_event("ui.hud.save", 240)
	var saved_evt := await _wait_for_event(EVT_GAME_SAVED, 900)
	assert_bool(not save_ui_evt.is_empty()).is_true()
	assert_bool(_count_events("ui.hud.save") > save_source_count).is_true()
	assert_bool(not saved_evt.is_empty()).is_true()
	if saved_evt.is_empty():
		return
	btn_load.emit_signal("pressed")
	var loaded_evt := await _wait_for_event(EVT_GAME_LOADED, 900)
	assert_bool(not loaded_evt.is_empty()).is_true()
	if loaded_evt.is_empty():
		return

	var saved_payload := _parse_json_dict(str(saved_evt.get("data_json", "{}")))
	var loaded_payload := _parse_json_dict(str(loaded_evt.get("data_json", "{}")))
	assert_str(str(saved_payload.get("SaveSlotId", ""))).is_not_empty()
	assert_str(str(saved_payload.get("ContentPackId", ""))).is_not_empty()
	assert_int(int(saved_payload.get("ContentPackVersion", -1))).is_greater(0)
	assert_str(str(loaded_payload.get("SaveSlotId", ""))).is_equal(str(saved_payload.get("SaveSlotId", "")))
	assert_str(str(loaded_payload.get("ContentPackId", ""))).is_equal(str(saved_payload.get("ContentPackId", "")))
	assert_int(int(loaded_payload.get("ContentPackVersion", -1))).is_equal(int(saved_payload.get("ContentPackVersion", -1)))
	assert_str(str(loaded_payload.get("GameId", ""))).is_not_empty()
	assert_bool(menu.visible).is_false()
	assert_bool((hud as CanvasItem).visible).is_true()

# ACC:T176.5
func test_task176_campaign_runmode_wiring_is_visible_in_start_payloads() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	_events.clear()
	var ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(ok).is_true()
	if not ok:
		return

	var menu_start_evt := await _wait_for_event(EVT_MENU_START, 240)
	assert_bool(not menu_start_evt.is_empty()).is_true()
	if menu_start_evt.is_empty():
		return

	var start_payload := _parse_json_dict(str(menu_start_evt.get("data_json", "{}")))
	assert_str(str(start_payload.get("run_mode", ""))).is_equal("campaign")
	assert_str(str(start_payload.get("run_mode", ""))).is_not_empty()
	assert_str(str(start_payload.get("commander_id", ""))).is_not_empty()
	assert_str(str(start_payload.get("difficulty", ""))).is_not_empty()
	assert_str(str(start_payload.get("active_strategem_id", ""))).is_not_empty()
	assert_str(str(start_payload.get("passive_strategem_id", ""))).is_not_empty()
	assert_str(str(start_payload.get("run_mode", ""))).is_not_equal("sandbox")

# ACC:T176.6
func test_task176_boot_path_does_not_count_unrelated_gameplay_events_as_entry_evidence() -> void:
	var main := _create_main()
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(main)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var ok := MenuTestDriver.press_play_then_start(menu)
	assert_bool(ok).is_true()
	if not ok:
		return

	var turn_started := await _wait_for_event(EVT_TURN_STARTED, 360)
	assert_bool(not turn_started.is_empty()).is_true()

	var types := _event_types()
	assert_bool(types.has("core.sanguo.city.bought")).is_false()
	assert_bool(types.has("core.sanguo.economy.year.price.adjusted")).is_false()
	assert_bool(types.has("core.sanguo.game.ended")).is_false()

# ACC:T176.7
func test_task176_scope_mapping_lists_every_required_split_task() -> void:
	for path in [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"]:
		var task := _task176_from(path)
		if task.is_empty():
			continue
		var acceptance: Array = task.get("acceptance", [])
		var merged := ""
		for line in acceptance:
			merged += str(line) + "\n"
		for scope_id in ["T85", "T91", "T92", "T93", "T101", "T108", "T131", "T164", "T170"]:
			assert_bool(merged.find(scope_id) >= 0).is_true()

# ACC:T176.8
func test_task176_audit_refs_include_gdunit_and_contract_evidence_paths() -> void:
	for path in [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"]:
		var task := _task176_from(path)
		if task.is_empty():
			continue
		var test_refs: Array = task.get("test_refs", [])
		var ref_joined := _join_strings(test_refs)
		assert_bool(ref_joined.find("Tests.Godot/tests/UI/test_task176_mainmenu_boot_flow.gd") >= 0).is_true()
		assert_bool(ref_joined.find("Game.Core.Tests/Contracts/SanguoEventOrderingRulesTests.cs") >= 0).is_true()
		assert_bool(ref_joined.find("Game.Core.Tests/Contracts/SanguoEventContractsTests.cs") >= 0).is_true()

		var acceptance: Array = task.get("acceptance", [])
		for line in acceptance:
			assert_bool(str(line).find("Refs:") >= 0).is_true()

