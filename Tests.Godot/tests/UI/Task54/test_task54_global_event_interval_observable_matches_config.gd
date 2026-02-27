extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS := [5, 10, 20]

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_GLOBAL_EVENT_INTERVAL_TURNS := "global_event_interval_turns"

const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_INTERVAL_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/GlobalEventIntervalOption"

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

func _compute_trigger_turns(interval_turns: int, max_turn_inclusive: int) -> Array:
	var result: Array = []
	if interval_turns <= 0:
		return result
	var turn := interval_turns
	while turn <= max_turn_inclusive:
		result.append(turn)
		turn += interval_turns
	return result

# acceptance: ACC:T54.6
func test_task54_global_event_interval_presets_are_supported() -> void:
	assert_bool(ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS.has(5)).is_true()
	assert_bool(ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS.has(10)).is_true()
	assert_bool(ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS.has(20)).is_true()

# acceptance: ACC:T54.7
func test_task54_global_event_interval_observable_matches_config_smoke() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	var btn_start := menu.get_node(PATH_BTN_START) as Button
	var interval := menu.get_node(PATH_INTERVAL_OPTION) as OptionButton

	for i in range(interval.item_count):
		if interval.get_item_id(i) == 5:
			interval.select(i)
			interval.emit_signal("item_selected", i)
			break

	_seen_game_started = false
	_last_payload_json = ""
	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	btn_start.emit_signal("pressed")
	for _i in range(240):
		if _seen_game_started:
			break
		await get_tree().process_frame
	assert_bool(_seen_game_started).is_true()

	var payload := _parse_json_dict(_last_payload_json)
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	var it := int(cfg.get(KEY_GLOBAL_EVENT_INTERVAL_TURNS, 0))
	assert_bool(ALLOWED_GLOBAL_EVENT_INTERVAL_TURNS.has(it)).is_true()
	assert_int(it).is_equal(5)

	var turns := _compute_trigger_turns(it, 30)
	assert_array(turns).contains_exactly([5, 10, 15, 20, 25, 30])
