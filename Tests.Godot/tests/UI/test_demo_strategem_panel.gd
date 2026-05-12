extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_GAME_STARTED := "core.sanguo.game.started"
const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_PLAYER_STATE_CHANGED := "core.sanguo.player.state.changed"
const EVENT_UI_STRATEGEM_USE := "ui.sanguo.strategem.use"
const PATH_MAIN := "res://Game.Godot/Scenes/Main.tscn"
const PATH_HUD := "SplitRoot/TopArea/HudLayer/HUD"
const PATH_MENU := "MenuLayer/MainMenu"
const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_ACTIVE_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/ActiveStrategemOption"
const PATH_PASSIVE_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PassiveStrategemOption"

var _seen_ui_strategem_use := false

func before_test() -> void:
	await _setup_event_bus()
	_seen_ui_strategem_use = false

func after_test() -> void:
	await _teardown_event_bus()

func _publish_game_started(active_id: String, passive_id: String) -> void:
	var payload := "{\"game_start_config\":{\"run_mode\":\"campaign\",\"commander_id\":\"c_liu_bei\",\"difficulty\":\"normal\",\"active_strategem_id\":\"%s\",\"passive_strategem_id\":\"%s\",\"players_count\":4,\"starting_money_preset\":10000,\"character_assignments\":{\"p1\":\"c_liu_bei\"}}}" % [active_id, passive_id]
	_bus.PublishSimple(EVENT_GAME_STARTED, "ut", payload)

func _publish_turn_started(player_id: String) -> void:
	_bus.PublishSimple(EVENT_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"%s\",\"Year\":3,\"Month\":2,\"Day\":1,\"TurnNumber\":1}" % player_id)

func _wait_frames(count: int = 4) -> void:
	for _i in range(count):
		await get_tree().process_frame

func _select_option_by_metadata(option: OptionButton, expected_id: String) -> void:
	for i in range(option.item_count):
		if str(option.get_item_metadata(i)) == expected_id:
			option.select(i)
			return
	fail("option metadata not found: %s" % expected_id)

func _start_main_with_strategems(active_id: String, passive_id: String) -> Node:
	var main := preload(PATH_MAIN).instantiate()
	add_child(main)
	_tracked_nodes.append(main)
	await get_tree().process_frame

	var menu := main.get_node(PATH_MENU)
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	var btn_start := menu.get_node(PATH_BTN_START) as Button
	var active_option := menu.get_node(PATH_ACTIVE_OPTION) as OptionButton
	var passive_option := menu.get_node(PATH_PASSIVE_OPTION) as OptionButton
	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	_select_option_by_metadata(active_option, active_id)
	_select_option_by_metadata(passive_option, passive_id)
	btn_start.emit_signal("pressed")
	await _wait_frames(12)
	return main

func test_demo_strategem_panel_shows_passive_name_and_description() -> void:
	var hud := await _hud()
	_publish_game_started("strat_active_bonus_gold", "strat_passive_bonus_hp")
	await _wait_frames()

	var passive_name: Label = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/PassiveStrategemName")
	var passive_desc: Label = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/PassiveStrategemDescription")

	assert_str(passive_name.text).contains("增加体力")
	assert_str(passive_desc.text).contains("HP max +10")

func test_demo_strategem_button_is_disabled_when_not_player_turn() -> void:
	var hud := await _hud()
	_publish_game_started("strat_active_bonus_gold", "strat_passive_rich")
	await _wait_frames()

	var button: Button = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/ActiveStrategemButton")
	var status: Label = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/ActiveStrategemStatus")

	assert_bool(button.disabled).is_true()
	assert_str(status.text).contains("Wait for your turn")

func test_demo_strategem_button_is_enabled_on_player_turn_and_disables_after_use() -> void:
	_connect_domain_event_emitted(Callable(self, "_on_demo_domain_event"))

	var hud := await _hud()
	_publish_game_started("strat_active_bonus_gold", "strat_passive_rich")
	_publish_turn_started("p1")
	await _wait_frames()

	var button: Button = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/ActiveStrategemButton")
	var status: Label = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/ActiveStrategemStatus")

	assert_bool(button.disabled).is_false()
	assert_str(status.text).contains("Ready this round")

	button.emit_signal("pressed")
	await _wait_frames()

	assert_bool(_seen_ui_strategem_use).is_true()
	assert_bool(button.disabled).is_true()
	assert_str(status.text).contains("Used this round")

func test_demo_strategem_money_effect_updates_active_player_money() -> void:
	_connect_domain_event_emitted(Callable(self, "_on_demo_domain_event"))
	var main := await _start_main_with_strategems("strat_active_bonus_gold", "strat_passive_rich")
	var hud := main.get_node(PATH_HUD)
	await _wait_frames(6)

	var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
	var button: Button = hud.get_node("TopBar/TopStack/StrategemPanel/VBox/ActiveStrategemButton")

	assert_str(money_label.text).contains("10100")
	button.emit_signal("pressed")
	await _wait_frames(12)

	assert_str(money_label.text).contains("10130")

func _on_demo_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	if str(type) == EVENT_UI_STRATEGEM_USE:
		_seen_ui_strategem_use = true
