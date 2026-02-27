extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_MENU_START := "ui.menu.start"
const KEY_MAP_ID := "map_id"
const KEY_PLAYERS_COUNT := "players_count"
const KEY_STARTING_MONEY_PRESET := "starting_money_preset"
const KEY_GLOBAL_EVENT_INTERVAL_TURNS := "global_event_interval_turns"
const KEY_RANDOM_SEED := "random_seed"
const KEY_CHARACTER_ASSIGNMENTS := "character_assignments"

const ALLOWED_PLAYERS_COUNTS := [2, 3, 4]
const ALLOWED_STARTING_MONEY_PRESETS := [5000, 10000, 20000]
const ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS := [5, 10, 20]

const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_MAP_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/MapOption"
const PATH_PLAYERS_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PlayersOption"
const PATH_MONEY_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/StartingMoneyOption"
const PATH_INTERVAL_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/GlobalEventIntervalOption"
const PATH_CHAR_GRID := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/CharacterCarousel/CharacterGrid"

var _bus: Node
var _seen_menu_start := false
var _last_payload_json := ""

func before_test() -> void:
	_seen_menu_start = false
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
	get_tree().get_root().add_child(_bus)
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func after_test() -> void:
	if is_instance_valid(_bus):
		_bus.queue_free()

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	if str(type) == EVENT_TYPE_MENU_START:
		_seen_menu_start = true
		_last_payload_json = str(data_json)

func _parse_json_dict(json_text: String) -> Dictionary:
	var text := json_text.strip_edges()
	if text == "":
		return {}
	var v: Variant = JSON.parse_string(text)
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

func _assert_option_ids(option: OptionButton, expected_ids: Array) -> void:
	var got: Array = []
	for i in range(option.item_count):
		got.append(option.get_item_id(i))
	assert_array(got).is_equal(expected_ids)

func _find_menu_nodes(menu: Node) -> Dictionary:
	return {
		"play": menu.get_node(PATH_BTN_PLAY),
		"start": menu.get_node(PATH_BTN_START),
		"map": menu.get_node(PATH_MAP_OPTION),
		"players": menu.get_node(PATH_PLAYERS_OPTION),
		"money": menu.get_node(PATH_MONEY_OPTION),
		"interval": menu.get_node(PATH_INTERVAL_OPTION),
		"char_grid": menu.get_node(PATH_CHAR_GRID),
	}

# acceptance: ACC:T54.1
func test_task54_new_game_setup_presets_are_whitelisted_and_defaults_are_valid() -> void:
	var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
	add_child(auto_free(menu))
	await get_tree().process_frame

	var nodes := _find_menu_nodes(menu)
	var players: OptionButton = nodes["players"]
	var money: OptionButton = nodes["money"]
	var interval: OptionButton = nodes["interval"]
	var map: OptionButton = nodes["map"]
	var char_grid: GridContainer = nodes["char_grid"]

	_assert_option_ids(players, ALLOWED_PLAYERS_COUNTS)
	_assert_option_ids(money, ALLOWED_STARTING_MONEY_PRESETS)
	_assert_option_ids(interval, ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS)

	assert_int(map.item_count).is_greater(0)
	assert_int(char_grid.get_child_count()).is_equal(8)

	assert_int(players.get_item_id(players.selected)).is_equal(2)
	assert_int(money.get_item_id(money.selected)).is_equal(10000)
	assert_int(interval.get_item_id(interval.selected)).is_equal(10)

# acceptance: ACC:T54.2
func test_task54_start_publishes_unique_character_assignments_for_all_players() -> void:
	var bus := get_node_or_null("/root/EventBus")
	assert_object(bus).is_not_null()
	assert_bool(bus.has_method("PublishSimple")).is_true()

	_seen_menu_start = false
	_last_payload_json = ""
	bus.call("PublishSimple", EVENT_TYPE_MENU_START, "ut", "{\"ok\":true}")
	await get_tree().process_frame
	assert_bool(_seen_menu_start).is_true()

	_seen_menu_start = false
	_last_payload_json = ""

	var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
	add_child(auto_free(menu))
	await get_tree().process_frame

	var nodes := _find_menu_nodes(menu)
	var btn_play: Button = nodes["play"]
	var btn_start: Button = nodes["start"]
	var players: OptionButton = nodes["players"]
	var money: OptionButton = nodes["money"]
	var interval: OptionButton = nodes["interval"]

	for i in range(players.item_count):
		if players.get_item_id(i) == 4:
			players.select(i)
			players.emit_signal("item_selected", i)
			break
	for i in range(money.item_count):
		if money.get_item_id(i) == 20000:
			money.select(i)
			money.emit_signal("item_selected", i)
			break
	for i in range(interval.item_count):
		if interval.get_item_id(i) == 20:
			interval.select(i)
			interval.emit_signal("item_selected", i)
			break

	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	btn_start.emit_signal("pressed")
	for _i in range(120):
		if _seen_menu_start:
			break
		await get_tree().process_frame

	if not _seen_menu_start:
		var status := menu.get_node_or_null("StatusLabel") as Label
		if status != null:
			print("T54: menu did not emit ui.menu.start; status='%s'" % status.text)
		assert_bool(false).is_true()
		return

	var payload := _parse_json_dict(_last_payload_json)
	assert_bool(payload.has(KEY_MAP_ID)).is_true()
	assert_bool(payload.has(KEY_PLAYERS_COUNT)).is_true()
	assert_bool(payload.has(KEY_STARTING_MONEY_PRESET)).is_true()
	assert_bool(payload.has(KEY_GLOBAL_EVENT_INTERVAL_TURNS)).is_true()
	assert_bool(payload.has(KEY_RANDOM_SEED)).is_true()
	assert_bool(payload.has(KEY_CHARACTER_ASSIGNMENTS)).is_true()

	assert_str(str(payload.get(KEY_MAP_ID, ""))).is_not_empty()
	assert_int(int(payload.get(KEY_PLAYERS_COUNT, 0))).is_between(2, 4)
	assert_bool(ALLOWED_STARTING_MONEY_PRESETS.has(int(payload.get(KEY_STARTING_MONEY_PRESET, 0)))).is_true()
	assert_bool(ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS.has(int(payload.get(KEY_GLOBAL_EVENT_INTERVAL_TURNS, 0)))).is_true()

	var assigns_v: Variant = payload.get(KEY_CHARACTER_ASSIGNMENTS)
	if not (assigns_v is Dictionary):
		assert_bool(false).is_true()
		return
	var assigns: Dictionary = assigns_v as Dictionary
	var players_count := int(payload.get(KEY_PLAYERS_COUNT, 0))
	assert_int(assigns.size()).is_equal(players_count)
	assert_bool(_has_unique_non_empty_assignments(assigns)).is_true()
	assert_str(str(assigns.get("p1", ""))).is_not_empty()
