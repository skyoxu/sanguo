extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const EVENT_TYPE_PLAYER_STATE_CHANGED := "core.sanguo.player.state.changed"
const EVENT_TYPE_HEALTH_UPDATED := "core.health.updated"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_ACTIVE_STRATEGEM_ID := "active_strategem_id"
const KEY_PASSIVE_STRATEGEM_ID := "passive_strategem_id"

const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_ACTIVE_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/ActiveStrategemOption"
const PATH_PASSIVE_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PassiveStrategemOption"

var _bus: Node
var _seen_game_started := false
var _last_payload_json := ""
var _player_state_payloads: Array = []
var _health_payloads: Array = []

func before() -> void:
	_seen_game_started = false
	_last_payload_json = ""
	_player_state_payloads.clear()
	_health_payloads.clear()

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
	elif str(type) == EVENT_TYPE_PLAYER_STATE_CHANGED:
		_player_state_payloads.append(str(data_json))
	elif str(type) == EVENT_TYPE_HEALTH_UPDATED:
		_health_payloads.append(str(data_json))

func _parse_json_dict(json_text: String) -> Dictionary:
	var v: Variant = JSON.parse_string(json_text)
	if typeof(v) != TYPE_DICTIONARY:
		return {}
	return v as Dictionary

func _select_option_by_metadata(option: OptionButton, expected_id: String) -> void:
	for i in range(option.item_count):
		if str(option.get_item_metadata(i)) == expected_id:
			option.select(i)
			return
	fail("option metadata not found: %s" % expected_id)

func _start_with_strategems(menu: Node, active_id: String, passive_id: String) -> void:
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	var btn_start := menu.get_node(PATH_BTN_START) as Button
	var active_option := menu.get_node(PATH_ACTIVE_OPTION) as OptionButton
	var passive_option := menu.get_node(PATH_PASSIVE_OPTION) as OptionButton
	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	_select_option_by_metadata(active_option, active_id)
	_select_option_by_metadata(passive_option, passive_id)
	_seen_game_started = false
	_last_payload_json = ""
	_player_state_payloads.clear()
	_health_payloads.clear()
	btn_start.emit_signal("pressed")
	for _i in range(240):
		if _seen_game_started and _player_state_payloads.size() > 0:
			break
		await get_tree().process_frame

func test_temp_strategem_options_show_all_four_entries() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	btn_play.emit_signal("pressed")
	await get_tree().process_frame

	var active_option := menu.get_node(PATH_ACTIVE_OPTION) as OptionButton
	var passive_option := menu.get_node(PATH_PASSIVE_OPTION) as OptionButton

	assert_int(active_option.item_count).is_equal(2)
	assert_int(passive_option.item_count).is_equal(2)
	assert_str(str(active_option.get_item_metadata(0))).is_equal("strat_active_bonus_gold")
	assert_str(str(active_option.get_item_metadata(1))).is_equal("strat_active_reduce_pressure")
	assert_str(str(passive_option.get_item_metadata(0))).is_equal("strat_passive_bonus_hp")
	assert_str(str(passive_option.get_item_metadata(1))).is_equal("strat_passive_rich")

func test_temp_strategem_start_payload_carries_selected_ids() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	await _start_with_strategems(menu, "strat_active_reduce_pressure", "strat_passive_rich")

	assert_bool(_seen_game_started).is_true()
	var payload := _parse_json_dict(_last_payload_json)
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	assert_str(str(cfg.get(KEY_ACTIVE_STRATEGEM_ID, ""))).is_equal("strat_active_reduce_pressure")
	assert_str(str(cfg.get(KEY_PASSIVE_STRATEGEM_ID, ""))).is_equal("strat_passive_rich")

func test_temp_strategem_gold_effects_change_opening_money_and_hp() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	await _start_with_strategems(menu, "strat_active_bonus_gold", "strat_passive_bonus_hp")

	assert_bool(_seen_game_started).is_true()
	assert_bool(_player_state_payloads.size() > 0).is_true()
	assert_bool(_health_payloads.size() > 0).is_true()

	var player_state := _parse_json_dict(str(_player_state_payloads[0]))
	var health_state := _parse_json_dict(str(_health_payloads[0]))

	assert_str(str(player_state.get("PlayerId", ""))).is_equal("p1")
	assert_int(int(player_state.get("Money", 0))).is_equal(10000)
	assert_int(int(health_state.get("value", 0))).is_equal(110)
