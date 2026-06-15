extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"
const UI_DICE_ROLL := "ui.hud.dice.roll"
const UI_TILE_ACTION_SELECTED := "ui.sanguo.tile.action.selected"

const CORE_TURN_STARTED := "core.sanguo.game.turn.started"
const CORE_TOKEN_MOVED := "core.sanguo.board.token.moved"
const CORE_COMBAT_STARTED := "core.sanguo.combat.started"
const CORE_COMBAT_ENDED := "core.sanguo.combat.ended"
const CORE_PLAYER_STATE_CHANGED := "core.sanguo.player.state.changed"
const CORE_HEALTH_UPDATED := "core.health.updated"

var _bus: Node
var _events: Array = []


func before() -> void:
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
	_events = []


func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	_events.append({"type": str(type), "data_json": str(data_json)})


func _last_event(type_name: String) -> Dictionary:
	for i in range(_events.size() - 1, -1, -1):
		var e: Dictionary = _events[i]
		if str(e.get("type", "")) == type_name:
			return e
	return {}


func _events_of_type(type_name: String) -> Array:
	var out: Array = []
	for e in _events:
		if str(e.get("type", "")) == type_name:
			out.append(e)
	return out


func _wait_for_event(type_name: String, max_frames: int = 180) -> void:
	for _i in range(max_frames):
		if _last_event(type_name).size() > 0:
			return
		await get_tree().process_frame
	assert_bool(_last_event(type_name).size() > 0).is_true()


func _wait_for_event_from(type_name: String, from_index: int, max_frames: int = 180) -> Dictionary:
	for _i in range(max_frames):
		for index in range(from_index, _events.size()):
			var e: Dictionary = _events[index]
			if str(e.get("type", "")) == type_name:
				return e
		await get_tree().process_frame
	assert_bool(false).is_true()
	return {}


func _wait_for_event_for_corr(type_name: String, correlation_id: String, max_frames: int = 180) -> Dictionary:
	for _i in range(max_frames):
		for e in _events_of_type(type_name):
			var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
			if str(payload.get("CorrelationId", "")) == correlation_id:
				return payload
		await get_tree().process_frame
	assert_bool(false).is_true()
	return {}


func _wait_for_health_event_for_corr(correlation_id: String, from_index: int = 0, max_frames: int = 180) -> Dictionary:
	for _i in range(max_frames):
		for index in range(from_index, _events.size()):
			var e: Dictionary = _events[index]
			if str(e.get("type", "")) != CORE_HEALTH_UPDATED:
				continue
			var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
			if str(payload.get("correlationId", "")) == correlation_id:
				return payload
		await get_tree().process_frame
	assert_bool(false).is_true()
	return {}


func _wait_for_turn_started(active_player_id: String, max_frames: int = 300) -> void:
	for _i in range(max_frames):
		for e in _events_of_type(CORE_TURN_STARTED):
			var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
			if str(payload.get("ActivePlayerId", "")) == active_player_id:
				return
		await get_tree().process_frame
	assert_bool(false).is_true()


func _wait_for_turn_started_from(active_player_id: String, from_index: int, max_frames: int = 300) -> void:
	for _i in range(max_frames):
		for index in range(from_index, _events.size()):
			var e: Dictionary = _events[index]
			if str(e.get("type", "")) != CORE_TURN_STARTED:
				continue
			var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
			if str(payload.get("ActivePlayerId", "")) == active_player_id:
				return
		await get_tree().process_frame
	assert_bool(false).is_true()


func _wait_for_enabled_button(button: Button, max_frames: int = 120) -> void:
	for _i in range(max_frames):
		if not button.disabled:
			return
		await get_tree().process_frame
	assert_bool(button.disabled).is_false()


func _assert_returned_to_main_loop(main: Node, active_player_id: String, max_frames: int = 600) -> void:
	var battle_view: Control = main.get_node("SplitRoot/BottomArea/BoardArea/Overlays/SanguoBattleView")
	assert_bool(battle_view.visible).is_true()
	var continue_btn: Button = battle_view.get_node("Panel/VBox/ContinueButton")
	assert_bool(continue_btn.disabled).is_false()
	continue_btn.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(battle_view.visible).is_false()
	await _wait_for_turn_started(active_player_id, max_frames)


func _start_config_json(seed: int) -> String:
	return "{\"map_id\":\"map001\",\"players_count\":4,\"starting_money_preset\":5000,\"global_event_interval_turns\":5,\"random_seed\":%d,\"character_assignments\":{\"p1\":\"c_zhao_yun\",\"ai-1\":\"c_cao_cao\",\"ai-2\":\"c_sun_quan\",\"ai-3\":\"c_yuan_shao\"}}" % seed


# ACC:T59.3
# ACC:T59.4
func test_task59_roundtrip_enters_battle_view_and_returns_to_map_and_allows_continue() -> void:
	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var controller := main.get_node_or_null("SanguoGameLoopController")
	if controller != null:
		controller.set("AiAutoAdvanceDelaySeconds", 0.02)
		controller.set("AiAutoAdvanceDelaySecondsWhenSkip", 0.02)

	_bus.PublishSimple(UI_MENU_START, "ut", _start_config_json(7))
	await _wait_for_turn_started("p1", 240)

	var hud := main.get_node("SplitRoot/TopArea/HudLayer/HUD")
	var dice: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")
	dice.emit_signal("pressed")

	await _wait_for_event(UI_DICE_ROLL, 120)
	var ui_evt := _last_event(UI_DICE_ROLL)
	var ui_payload: Dictionary = JSON.parse_string(str(ui_evt.get("data_json", "{}")))
	var corr := str(ui_payload.get("CorrelationId", ""))
	assert_bool(corr.length() > 0).is_true()

	var moved_payload := await _wait_for_event_for_corr(CORE_TOKEN_MOVED, corr, 240)
	var to_index := int(moved_payload.get("ToIndex", -1))
	assert_int(to_index).is_equal(6)

	_bus.PublishSimple(UI_TILE_ACTION_SELECTED, "ut",
		"{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"ToIndex\":%d,\"Action\":\"start_combat\",\"CorrelationId\":\"%s\",\"CausationId\":\"%s\"}" % [to_index, corr, UI_TILE_ACTION_SELECTED])

	await _wait_for_event_for_corr(CORE_COMBAT_STARTED, corr, 240)
	await _wait_for_event_for_corr(CORE_COMBAT_ENDED, corr, 240)

	var money_after := 0.0
	for e in _events_of_type(CORE_PLAYER_STATE_CHANGED):
		var payload: Dictionary = JSON.parse_string(str(e.get("data_json", "{}")))
		if str(payload.get("CorrelationId", "")) == corr and str(payload.get("PlayerId", "")) == "p1":
			money_after = float(payload.get("Money", 0.0))
	assert_bool(money_after > 5000.0).is_true()

	var battle_view: Control = main.get_node("SplitRoot/BottomArea/BoardArea/Overlays/SanguoBattleView")
	assert_bool(battle_view.visible).is_true()

	var continue_btn: Button = battle_view.get_node("Panel/VBox/ContinueButton")
	assert_bool(continue_btn.disabled).is_false()
	continue_btn.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(battle_view.visible).is_false()

	await _wait_for_turn_started("p1", 600)
	_events = []
	dice.emit_signal("pressed")
	await _wait_for_event(UI_DICE_ROLL, 180)


# ACC:T182.1
# ACC:T182.2
# ACC:T182.3
# ACC:T182.4
# ACC:T182.10
# ACC:T224.1 ACC:T224.2 ACC:T224.3 ACC:T224.4 ACC:T224.5
func test_task182_win_combat_keeps_combat_end_hp_on_return() -> void:
	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var controller := main.get_node_or_null("SanguoGameLoopController")
	if controller != null:
		controller.set("AiAutoAdvanceDelaySeconds", 0.02)
		controller.set("AiAutoAdvanceDelaySecondsWhenSkip", 0.02)

	var win_start := "{\"map_id\":\"map001\",\"players_count\":4,\"starting_money_preset\":5000,\"global_event_interval_turns\":5,\"random_seed\":7,\"character_assignments\":{\"p1\":\"c_lu_bu\",\"ai-1\":\"c_cao_cao\",\"ai-2\":\"c_sun_quan\",\"ai-3\":\"c_sima_yi\"}}"
	_bus.PublishSimple(UI_MENU_START, "ut", win_start)
	await _wait_for_turn_started("p1", 240)

	var hud := main.get_node("SplitRoot/TopArea/HudLayer/HUD")
	var hp_label: Label = hud.get_node("TopBar/TopStack/HBox/HealthLabel")
	var dice: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")
	dice.emit_signal("pressed")

	await _wait_for_event(UI_DICE_ROLL, 120)
	var win_ui := _last_event(UI_DICE_ROLL)
	var win_ui_payload: Dictionary = JSON.parse_string(str(win_ui.get("data_json", "{}")))
	var win_corr := str(win_ui_payload.get("CorrelationId", ""))
	assert_bool(win_corr.length() > 0).is_true()
	var win_moved := await _wait_for_event_for_corr(CORE_TOKEN_MOVED, win_corr, 240)
	var win_to_index := int(win_moved.get("ToIndex", -1))
	assert_int(win_to_index).is_equal(6)

	_bus.PublishSimple(UI_TILE_ACTION_SELECTED, "ut",
		"{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"ToIndex\":%d,\"Action\":\"start_combat\",\"CorrelationId\":\"%s\",\"CausationId\":\"%s\"}" % [win_to_index, win_corr, UI_TILE_ACTION_SELECTED])
	await _wait_for_event_for_corr(CORE_COMBAT_STARTED, win_corr, 240)
	var win_ended := await _wait_for_event_for_corr(CORE_COMBAT_ENDED, win_corr, 240)
	var win_result: Dictionary = win_ended.get("Result", {})
	var win_snapshot: Dictionary = win_result.get("PlayerSnapshot", {})
	var win_main: Dictionary = win_snapshot.get("MainUnit", {})
	var win_stats: Dictionary = win_main.get("Stats", {})
	var win_current_hp := int(win_stats.get("CurrentHP", -1))
	assert_bool(win_current_hp > 0).is_true()
	var win_health_payload := await _wait_for_health_event_for_corr(win_corr, 0, 180)
	var win_reported_hp := int(win_health_payload.get("value", -1))
	assert_int(win_reported_hp).is_equal(win_current_hp)
	assert_str(hp_label.text).contains(str(win_reported_hp))
	await _assert_returned_to_main_loop(main, "p1", 600)

# ACC:T182.5
# ACC:T182.6
# ACC:T182.7
# ACC:T182.8
# ACC:T182.9
func test_task182_loss_combat_restores_half_max_hp_on_return() -> void:
	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame

	var controller := main.get_node_or_null("SanguoGameLoopController")
	if controller != null:
		controller.set("AiAutoAdvanceDelaySeconds", 0.02)
		controller.set("AiAutoAdvanceDelaySecondsWhenSkip", 0.02)

	var hud := main.get_node("SplitRoot/TopArea/HudLayer/HUD")
	var hp_label: Label = hud.get_node("TopBar/TopStack/HBox/HealthLabel")
	var dice: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")

	var lose_start := "{\"map_id\":\"map001\",\"players_count\":4,\"starting_money_preset\":5000,\"global_event_interval_turns\":5,\"random_seed\":7,\"character_assignments\":{\"p1\":\"c_zhuge_liang\",\"ai-1\":\"c_lu_bu\",\"ai-2\":\"c_cao_cao\",\"ai-3\":\"c_sun_quan\"}}"
	_bus.PublishSimple(UI_MENU_START, "ut", lose_start)
	await _wait_for_turn_started("p1", 240)
	await _wait_for_enabled_button(dice, 180)
	var roll_event_start := _events.size()
	dice.emit_signal("pressed")
	var lose_ui := await _wait_for_event_from(UI_DICE_ROLL, roll_event_start, 180)
	var lose_ui_payload: Dictionary = JSON.parse_string(str(lose_ui.get("data_json", "{}")))
	var lose_corr := str(lose_ui_payload.get("CorrelationId", ""))
	assert_bool(lose_corr.length() > 0).is_true()
	var lose_moved := await _wait_for_event_for_corr(CORE_TOKEN_MOVED, lose_corr, 240)
	var lose_to_index := int(lose_moved.get("ToIndex", -1))
	assert_int(lose_to_index).is_equal(6)
	var health_event_start := _events.size()

	_bus.PublishSimple(UI_TILE_ACTION_SELECTED, "ut",
		"{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"ToIndex\":%d,\"Action\":\"start_combat\",\"CorrelationId\":\"%s\",\"CausationId\":\"%s\"}" % [lose_to_index, lose_corr, UI_TILE_ACTION_SELECTED])
	await _wait_for_event_for_corr(CORE_COMBAT_STARTED, lose_corr, 240)
	var lose_ended := await _wait_for_event_for_corr(CORE_COMBAT_ENDED, lose_corr, 240)
	var lose_result: Dictionary = lose_ended.get("Result", {})
	var lose_snapshot: Dictionary = lose_result.get("PlayerSnapshot", {})
	var lose_main: Dictionary = lose_snapshot.get("MainUnit", {})
	var lose_stats: Dictionary = lose_main.get("Stats", {})
	var lose_max_hp := int(lose_stats.get("MaxHP", -1))
	assert_bool(lose_max_hp > 0).is_true()
	var lose_health_payload := await _wait_for_health_event_for_corr(lose_corr, health_event_start, 180)
	var lose_reported_hp := int(lose_health_payload.get("value", -1))
	assert_int(lose_reported_hp).is_equal(int(lose_max_hp / 2))
	assert_str(hp_label.text).contains(str(lose_reported_hp))
	await _assert_returned_to_main_loop(main, "p1", 600)
