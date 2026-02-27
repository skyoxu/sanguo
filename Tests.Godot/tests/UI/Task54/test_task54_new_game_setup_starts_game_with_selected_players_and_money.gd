extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_RANDOM_SEED := "random_seed"
const KEY_MAP_ID := "map_id"
const KEY_PLAYERS_COUNT := "players_count"
const KEY_STARTING_MONEY_PRESET := "starting_money_preset"
const KEY_GLOBAL_EVENT_INTERVAL_TURNS := "global_event_interval_turns"
const KEY_CHARACTER_ASSIGNMENTS := "character_assignments"

const VALID_PLAYERS_COUNTS := [2, 3, 4]
const VALID_STARTING_MONEY_PRESETS := [5000, 10000, 20000]
const VALID_GLOBAL_EVENT_INTERVAL_TURNS := [5, 10, 20]

const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_PLAYERS_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PlayersOption"
const PATH_MONEY_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/StartingMoneyOption"

var _bus: Node
var _seen_game_started := false
var _last_payload_json := ""

func before() -> void:
	_seen_game_started = false
	_last_payload_json = ""

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	var existing_cr := get_node_or_null("/root/CompositionRoot")
	if existing_cr != null:
		existing_cr.name = "CompositionRoot__old__%s" % str(Time.get_ticks_msec())
		existing_cr.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	if str(type) == EVENT_TYPE_GAME_STARTED:
		_seen_game_started = true
		_last_payload_json = str(data_json)

func _parse_json_dict(json_text: String) -> Dictionary:
	var v: Variant = JSON.parse_string(json_text)
	if typeof(v) != TYPE_DICTIONARY:
		return {}
	return v as Dictionary

func _has_unique_non_empty_assignments(assignments: Dictionary) -> bool:
	var seen_character_ids: Dictionary = {}
	for player_id in assignments.keys():
		var player_id_str := str(player_id).strip_edges()
		var character_id_str := str(assignments[player_id]).strip_edges()
		if player_id_str == "" or character_id_str == "":
			return false
		if seen_character_ids.has(character_id_str):
			return false
		seen_character_ids[character_id_str] = true
	return true

func _start_and_wait_game_started(menu: Node) -> void:
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	var btn_start := menu.get_node(PATH_BTN_START) as Button
	_seen_game_started = false
	_last_payload_json = ""
	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	btn_start.emit_signal("pressed")
	for _i in range(240):
		if _seen_game_started:
			break
		await get_tree().process_frame

# acceptance: ACC:T54.5
func test_task54_players_count_is_within_allowed_range_and_carried_in_started_config() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	var players := menu.get_node(PATH_PLAYERS_OPTION) as OptionButton

	for i in range(players.item_count):
		if players.get_item_id(i) == 3:
			players.select(i)
			players.emit_signal("item_selected", i)
			break

	await _start_and_wait_game_started(menu)
	assert_bool(_seen_game_started).is_true()
	var payload := _parse_json_dict(_last_payload_json)
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	var pc := int(cfg.get(KEY_PLAYERS_COUNT, 0))
	assert_bool(VALID_PLAYERS_COUNTS.has(pc)).is_true()
	assert_int(pc).is_equal(3)

# acceptance: ACC:T54.6
func test_task54_starting_money_preset_is_valid_and_carried_in_started_config() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	var money := menu.get_node(PATH_MONEY_OPTION) as OptionButton

	for i in range(money.item_count):
		if money.get_item_id(i) == 20000:
			money.select(i)
			money.emit_signal("item_selected", i)
			break

	await _start_and_wait_game_started(menu)
	assert_bool(_seen_game_started).is_true()
	var payload := _parse_json_dict(_last_payload_json)
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	var preset := int(cfg.get(KEY_STARTING_MONEY_PRESET, 0))
	assert_bool(VALID_STARTING_MONEY_PRESETS.has(preset)).is_true()
	assert_int(preset).is_equal(20000)

func test_task54_character_assignments_are_complete_and_unique() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	await _start_and_wait_game_started(menu)
	assert_bool(_seen_game_started).is_true()
	var payload := _parse_json_dict(_last_payload_json)
	assert_bool(payload.has(KEY_GAME_START_CONFIG)).is_true()
	assert_bool(payload.has(KEY_RANDOM_SEED)).is_true()
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	assert_str(str(cfg.get(KEY_MAP_ID, ""))).is_not_empty()
	assert_bool(VALID_GLOBAL_EVENT_INTERVAL_TURNS.has(int(cfg.get(KEY_GLOBAL_EVENT_INTERVAL_TURNS, 0)))).is_true()

	var pc := int(cfg.get(KEY_PLAYERS_COUNT, 0))
	assert_bool(VALID_PLAYERS_COUNTS.has(pc)).is_true()

	var assigns_v: Variant = cfg.get(KEY_CHARACTER_ASSIGNMENTS)
	assert_bool(assigns_v is Dictionary).is_true()
	var assigns: Dictionary = assigns_v as Dictionary
	assert_int(assigns.size()).is_equal(pc)
	assert_bool(_has_unique_non_empty_assignments(assigns)).is_true()
