extends "res://tests/Integration/Mvg/mainmenu_fixture.gd"

const EVT_GAME_STARTED := "core.sanguo.game.started"
const EVT_TURN_STARTED := "core.sanguo.game.turn.started"

func test_engine_input_opens_config_and_starts_sanguo_run() -> void:
	var menu := _menu()
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var play := menu.get_node(PLAY_PATH) as Button
	var start := menu.get_node(START_PATH) as Button
	var config := menu.get_node(CONFIG_PATH) as Control
	assert_object(play).is_not_null()
	assert_object(start).is_not_null()
	assert_object(config).is_not_null()
	if play == null or start == null or config == null:
		return

	if OS.get_environment("MVG_INPUT_CHALLENGE") == "disconnect-mainmenu-input":
		for connection in play.pressed.get_connections():
			play.pressed.disconnect(connection["callable"])

	assert_bool(await _activate(play)).is_true()
	var config_opened := await _wait_for(func() -> bool: return config.visible)
	assert_bool(config_opened).override_failure_message("MVG_MAINMENU_INPUT_DID_NOT_OPEN_CONFIG").is_true()
	if not config_opened:
		return

	var start_ready := await _wait_for(func() -> bool: return not start.disabled)
	assert_bool(start_ready).is_true()
	if not start_ready:
		return

	assert_bool(await _activate(start)).is_true()
	assert_bool(await _wait_for(func() -> bool: return _has_event(EVT_GAME_STARTED))).is_true()
	assert_bool(await _wait_for(func() -> bool: return _has_event(EVT_TURN_STARTED))).is_true()
	assert_bool(menu.visible).is_false()
