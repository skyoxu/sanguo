extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_UI_MENU_START := "ui.menu.start"
const EVENT_GAME_STARTED := "core.sanguo.game.started"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_ACTIVE_STRATEGEM_ID := "active_strategem_id"
const KEY_PASSIVE_STRATEGEM_ID := "passive_strategem_id"

const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"

var _bus: Node
var _seen_game_started := false
var _last_ui_menu_start_json := ""
var _last_game_started_json := ""
var _seen_types: Array = []

func before() -> void:
	_seen_game_started = false
	_last_ui_menu_start_json = ""
	_last_game_started_json = ""
	_seen_types = []

	var existing_bus := get_node_or_null("/root/EventBus")
	if existing_bus != null:
		existing_bus.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing_bus.queue_free()

	var existing_cr := get_node_or_null("/root/CompositionRoot")
	if existing_cr != null:
		existing_cr.name = "CompositionRoot__old__%s" % str(Time.get_ticks_msec())
		existing_cr.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	var event_type := str(type)
	if _seen_types.size() < 64:
		_seen_types.append(event_type)

	if event_type == EVENT_UI_MENU_START:
		_last_ui_menu_start_json = str(data_json)
	elif event_type == EVENT_GAME_STARTED:
		_seen_game_started = true
		_last_game_started_json = str(data_json)

func _parse_json_dict(json_text: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(json_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed as Dictionary

func _start_game_from_menu(menu: Node) -> void:
	var btn_play := menu.get_node_or_null(PATH_BTN_PLAY) as Button
	var btn_start := menu.get_node_or_null(PATH_BTN_START) as Button

	assert_object(btn_play).is_not_null()
	assert_object(btn_start).is_not_null()
	if btn_play == null or btn_start == null:
		return

	_last_ui_menu_start_json = ""
	_last_game_started_json = ""
	_seen_game_started = false

	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	btn_start.emit_signal("pressed")

	for _i in range(240):
		if _seen_game_started:
			break
		await get_tree().process_frame

# acceptance: ACC:T93.6
func test_task93_new_game_config_and_start_handoff_include_campaign_contract_fields() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node_or_null(PATH_MENU)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	await _start_game_from_menu(menu)

	assert_bool(_seen_game_started).is_true()
	assert_str(_last_ui_menu_start_json).is_not_empty()
	assert_str(_last_game_started_json).is_not_empty()
	if not _seen_game_started:
		print("Observed DomainEventEmitted types (first 64): %s" % str(_seen_types))
		return

	var ui_cfg := _parse_json_dict(_last_ui_menu_start_json)
	assert_bool(ui_cfg.has("map_id")).is_true()
	assert_bool(ui_cfg.has("players_count")).is_true()
	assert_bool(ui_cfg.has("random_seed")).is_true()

	assert_bool(ui_cfg.has("run_mode")).is_true()
	assert_str(str(ui_cfg.get("run_mode", ""))).is_equal("campaign")
	assert_bool(ui_cfg.has("commander_id")).is_true()
	assert_bool(ui_cfg.has("difficulty")).is_true()
	assert_bool(ui_cfg.has(KEY_ACTIVE_STRATEGEM_ID)).is_true()
	assert_bool(ui_cfg.has(KEY_PASSIVE_STRATEGEM_ID)).is_true()
	assert_str(str(ui_cfg.get(KEY_ACTIVE_STRATEGEM_ID, ""))).is_not_empty()
	assert_str(str(ui_cfg.get(KEY_PASSIVE_STRATEGEM_ID, ""))).is_not_empty()

	var started_payload := _parse_json_dict(_last_game_started_json)
	assert_bool(started_payload.has(KEY_GAME_START_CONFIG)).is_true()
	var handed_cfg_v: Variant = started_payload.get(KEY_GAME_START_CONFIG)
	assert_bool(handed_cfg_v is Dictionary).is_true()
	var handed_cfg: Dictionary = handed_cfg_v as Dictionary

	assert_bool(handed_cfg.has("run_mode")).is_true()
	assert_str(str(handed_cfg.get("run_mode", ""))).is_equal(str(ui_cfg.get("run_mode", "")))
	assert_str(str(handed_cfg.get("commander_id", ""))).is_equal(str(ui_cfg.get("commander_id", "")))
	assert_str(str(handed_cfg.get("difficulty", ""))).is_equal(str(ui_cfg.get("difficulty", "")))
	assert_str(str(handed_cfg.get(KEY_ACTIVE_STRATEGEM_ID, ""))).is_equal(str(ui_cfg.get(KEY_ACTIVE_STRATEGEM_ID, "")))
	assert_str(str(handed_cfg.get(KEY_PASSIVE_STRATEGEM_ID, ""))).is_equal(str(ui_cfg.get(KEY_PASSIVE_STRATEGEM_ID, "")))

func test_task93_start_handoff_keeps_shared_payload_fields_unchanged() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node_or_null(PATH_MENU)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	await _start_game_from_menu(menu)

	assert_bool(_seen_game_started).is_true()
	if not _seen_game_started:
		print("Observed DomainEventEmitted types (first 64): %s" % str(_seen_types))
		return

	var ui_cfg := _parse_json_dict(_last_ui_menu_start_json)
	var started_payload := _parse_json_dict(_last_game_started_json)
	var handed_cfg_v: Variant = started_payload.get(KEY_GAME_START_CONFIG)
	assert_bool(handed_cfg_v is Dictionary).is_true()
	var handed_cfg: Dictionary = handed_cfg_v as Dictionary

	assert_str(str(handed_cfg.get("map_id", ""))).is_equal(str(ui_cfg.get("map_id", "")))
	assert_int(int(handed_cfg.get("players_count", -1))).is_equal(int(ui_cfg.get("players_count", -2)))
	assert_int(int(handed_cfg.get("random_seed", -1))).is_equal(int(ui_cfg.get("random_seed", -2)))
