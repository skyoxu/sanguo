extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_GAME_STARTED := "core.sanguo.game.started"
const KEY_GAME_START_CONFIG := "game_start_config"
const KEY_ACTIVE_STRATEGEM_ID := "active_strategem_id"
const KEY_PASSIVE_STRATEGEM_ID := "passive_strategem_id"

const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"

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

# acceptance: ACC:T94.1
func test_task94_game_started_payload_carries_selected_strategems_in_start_config() -> void:
	var main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	await _start_and_wait_game_started(menu)

	assert_bool(_seen_game_started).is_true()
	var payload := _parse_json_dict(_last_payload_json)
	assert_bool(payload.has(KEY_GAME_START_CONFIG)).is_true()
	assert_bool(payload.get(KEY_GAME_START_CONFIG) is Dictionary).is_true()

	var cfg: Dictionary = payload.get(KEY_GAME_START_CONFIG, {})
	assert_bool(cfg.has(KEY_ACTIVE_STRATEGEM_ID)).is_true()
	assert_bool(cfg.has(KEY_PASSIVE_STRATEGEM_ID)).is_true()
	assert_str(str(cfg.get(KEY_ACTIVE_STRATEGEM_ID, ""))).is_not_empty()
	assert_str(str(cfg.get(KEY_PASSIVE_STRATEGEM_ID, ""))).is_not_empty()
