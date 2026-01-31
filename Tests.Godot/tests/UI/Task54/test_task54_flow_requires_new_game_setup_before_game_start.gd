extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const EVENT_TYPE_MENU_START := "ui.menu.start"
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

var _bus: Node
var _seen_game_started := false
var _seen_menu_start := false
var _last_started_payload_json := ""

func before() -> void:
	_seen_game_started = false
	_seen_menu_start = false
	_last_started_payload_json = ""

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
	var t := str(type)
	if t == EVENT_TYPE_MENU_START:
		_seen_menu_start = true
	if t == EVENT_TYPE_GAME_STARTED:
		_seen_game_started = true
		_last_started_payload_json = str(data_json)

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

# acceptance: ACC:T54.1
func test_task54_start_flow_uses_new_game_menu_config_and_emits_game_started() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node_or_null("MainMenu")
	assert_object(menu).is_not_null()

	var btn := menu.get_node("VBox/BtnPlay") as Button
	var players := menu.get_node("NewGameConfig/VBox/PlayersOption") as OptionButton
	var money := menu.get_node("NewGameConfig/VBox/StartingMoneyOption") as OptionButton
	var interval := menu.get_node("NewGameConfig/VBox/GlobalEventIntervalOption") as OptionButton
	var character := menu.get_node("NewGameConfig/VBox/CharacterOption") as OptionButton
	var map := menu.get_node("NewGameConfig/VBox/MapOption") as OptionButton

	# Pick a valid, non-default configuration (where possible).
	for i in range(players.item_count):
		if players.get_item_id(i) == 4:
			players.select(i)
			players.emit_signal("item_selected", i)
			break
	for i in range(money.item_count):
		if money.get_item_id(i) == 5000:
			money.select(i)
			money.emit_signal("item_selected", i)
			break
	for i in range(interval.item_count):
		if interval.get_item_id(i) == 20:
			interval.select(i)
			interval.emit_signal("item_selected", i)
			break

	_seen_menu_start = false
	_seen_game_started = false
	_last_started_payload_json = ""
	btn.emit_signal("pressed")

	for _i in range(240):
		if _seen_game_started:
			break
		await get_tree().process_frame

	assert_bool(_seen_menu_start).is_true()
	assert_bool(_seen_game_started).is_true()

	var started_payload := _parse_json_dict(_last_started_payload_json)
	assert_bool(started_payload.has(KEY_GAME_START_CONFIG)).is_true()
	assert_bool(started_payload.has(KEY_RANDOM_SEED)).is_true()
	assert_bool(started_payload.get(KEY_GAME_START_CONFIG) is Dictionary).is_true()

	var cfg: Dictionary = started_payload.get(KEY_GAME_START_CONFIG, {})
	assert_str(str(cfg.get(KEY_MAP_ID, ""))).is_not_empty()

	var pc := int(cfg.get(KEY_PLAYERS_COUNT, 0))
	assert_bool(VALID_PLAYERS_COUNTS.has(pc)).is_true()
	assert_int(pc).is_equal(players.get_item_id(players.selected))

	var preset := int(cfg.get(KEY_STARTING_MONEY_PRESET, 0))
	assert_bool(VALID_STARTING_MONEY_PRESETS.has(preset)).is_true()
	assert_int(preset).is_equal(money.get_item_id(money.selected))

	var it := int(cfg.get(KEY_GLOBAL_EVENT_INTERVAL_TURNS, 0))
	assert_bool(VALID_GLOBAL_EVENT_INTERVAL_TURNS.has(it)).is_true()
	assert_int(it).is_equal(interval.get_item_id(interval.selected))

	var seed := int(cfg.get(KEY_RANDOM_SEED, 0))
	assert_int(seed).is_equal(int(started_payload.get(KEY_RANDOM_SEED, -999)))

	var assigns_v: Variant = cfg.get(KEY_CHARACTER_ASSIGNMENTS)
	assert_bool(assigns_v is Dictionary).is_true()
	var assigns: Dictionary = assigns_v as Dictionary
	assert_int(assigns.size()).is_equal(pc)
	assert_bool(_has_unique_non_empty_assignments(assigns)).is_true()

	var selected_character_meta: Variant = character.get_item_metadata(character.selected)
	var selected_character_id := str(selected_character_meta)
	assert_str(selected_character_id).is_not_empty()
	assert_str(str(assigns.get("p1", ""))).is_equal(selected_character_id)

	var selected_map_meta: Variant = map.get_item_metadata(map.selected)
	var selected_map_id := str(selected_map_meta)
	assert_str(selected_map_id).is_not_empty()
	assert_str(str(cfg.get(KEY_MAP_ID, ""))).is_equal(selected_map_id)

# acceptance: ACC:T54.4
func test_task54_start_config_presets_are_whitelisted() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node("MainMenu")
	var players := menu.get_node("NewGameConfig/VBox/PlayersOption") as OptionButton
	var money := menu.get_node("NewGameConfig/VBox/StartingMoneyOption") as OptionButton
	var interval := menu.get_node("NewGameConfig/VBox/GlobalEventIntervalOption") as OptionButton

	var got_players: Array = []
	for i in range(players.item_count):
		got_players.append(players.get_item_id(i))
	assert_array(got_players).is_equal(VALID_PLAYERS_COUNTS)

	var got_money: Array = []
	for i in range(money.item_count):
		got_money.append(money.get_item_id(i))
	assert_array(got_money).is_equal(VALID_STARTING_MONEY_PRESETS)

	var got_interval: Array = []
	for i in range(interval.item_count):
		got_interval.append(interval.get_item_id(i))
	assert_array(got_interval).is_equal(VALID_GLOBAL_EVENT_INTERVAL_TURNS)

# acceptance: ACC:T54.5
func test_task54_menu_start_event_is_emitted_before_game_started() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node("MainMenu")
	var btn := menu.get_node("VBox/BtnPlay") as Button

	_seen_menu_start = false
	_seen_game_started = false
	btn.emit_signal("pressed")

	for _i in range(120):
		if _seen_menu_start:
			break
		await get_tree().process_frame
	assert_bool(_seen_menu_start).is_true()
