extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const EVENT_TYPE_TURN_STARTED := "core.sanguo.game.turn.started"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_RANDOM_SEED := "random_seed"
const KEY_MAP_ID := "map_id"
const KEY_PLAYERS_COUNT := "players_count"
const KEY_STARTING_MONEY_PRESET := "starting_money_preset"
const KEY_GLOBAL_EVENT_INTERVAL_TURNS := "global_event_interval_turns"
const KEY_CHARACTER_ASSIGNMENTS := "character_assignments"

var _bus: Node
var _seen_game_started := false
var _seen_turn_started := false
var _last_payload_json := ""
var _types: Array = []

func before() -> void:
	_seen_game_started = false
	_seen_turn_started = false
	_last_payload_json = ""
	_types = []

	# Install a temporary EventBus under /root to mimic Autoload
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	# Ensure prior suites didn't leave a failing CompositionRoot behind.
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
	if _types.size() < 64:
		_types.append(t)
	if t == EVENT_TYPE_TURN_STARTED:
		_seen_turn_started = true
	if t == EVENT_TYPE_GAME_STARTED:
		_seen_game_started = true
		_last_payload_json = str(data_json)

func _parse_json_dict(json_text: String) -> Dictionary:
	var v: Variant = JSON.parse_string(json_text)
	if typeof(v) != TYPE_DICTIONARY:
		return {}
	return v as Dictionary

func _assert_started_payload_shape(payload: Dictionary) -> void:
	assert_bool(payload.has(KEY_GAME_START_CONFIG)).is_true()
	assert_bool(payload.has(KEY_RANDOM_SEED)).is_true()
	assert_bool(payload.get(KEY_GAME_START_CONFIG) is Dictionary).is_true()
	var seed_value: Variant = payload.get(KEY_RANDOM_SEED)
	assert_bool(typeof(seed_value) == TYPE_INT or typeof(seed_value) == TYPE_FLOAT).is_true()
	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	assert_bool(cfg.has(KEY_MAP_ID)).is_true()
	assert_bool(cfg.has(KEY_PLAYERS_COUNT)).is_true()
	assert_bool(cfg.has(KEY_STARTING_MONEY_PRESET)).is_true()
	assert_bool(cfg.has(KEY_GLOBAL_EVENT_INTERVAL_TURNS)).is_true()
	assert_bool(cfg.has(KEY_RANDOM_SEED)).is_true()
	assert_bool(cfg.has(KEY_CHARACTER_ASSIGNMENTS)).is_true()

	assert_str(str(cfg.get(KEY_MAP_ID, ""))).is_not_empty()

	var players_count := int(cfg.get(KEY_PLAYERS_COUNT, 0))
	assert_int(players_count).is_between(2, 4)

	var preset := int(cfg.get(KEY_STARTING_MONEY_PRESET, 0))
	assert_bool(preset == 5000 or preset == 10000 or preset == 20000).is_true()

	var interval := int(cfg.get(KEY_GLOBAL_EVENT_INTERVAL_TURNS, 0))
	assert_bool(interval == 5 or interval == 10 or interval == 20).is_true()

	assert_int(int(seed_value)).is_equal(int(cfg.get(KEY_RANDOM_SEED)))

	var assigns_v: Variant = cfg.get(KEY_CHARACTER_ASSIGNMENTS)
	assert_bool(assigns_v is Dictionary).is_true()
	var assigns: Dictionary = assigns_v as Dictionary
	assert_int(assigns.size()).is_equal(players_count)

	var seen_chars: Dictionary = {}
	for k in assigns.keys():
		var cid := str(assigns.get(k))
		assert_str(cid).is_not_empty()
		assert_bool(seen_chars.has(cid)).is_false()
		seen_chars[cid] = true

# ACC:T50.3
func test_new_game_flow_publishes_game_started_with_reproducible_payload() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node_or_null("MainMenu")
	assert_object(menu).is_not_null()
	var btn := menu.get_node_or_null("VBox/BtnPlay")
	assert_object(btn).is_not_null()

	_seen_game_started = false
	_last_payload_json = ""
	btn.emit_signal("pressed")
	for _i in range(240):
		if _seen_game_started:
			break
		await get_tree().process_frame

	assert_bool(_seen_game_started).is_true()
	assert_bool(_seen_turn_started).is_true()
	if not _seen_game_started:
		print("Observed DomainEventEmitted types (first 64): %s" % str(_types))
		return
	var emitted_payload := _parse_json_dict(_last_payload_json)
	_assert_started_payload_shape(emitted_payload)
