extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func test_players_list_updates_for_all_players() -> void:
	var hud = await _hud()
	var list: VBoxContainer = hud.get_node("TopBar/TopStack/PlayersPanel/VBox/PlayersList")
	assert_int(list.get_child_count()).is_equal(0)

	_bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"Money\":120,\"PositionIndex\":1}")
	_bus.PublishSimple("core.sanguo.player.state.changed", "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"ai-2\",\"Money\":300,\"PositionIndex\":4}")

	for _i in range(10):
		await get_tree().process_frame
		if list.get_child_count() >= 2:
			break

	assert_int(list.get_child_count()).is_equal(2)
	var texts: Array = []
	for i in range(list.get_child_count()):
		var label: Label = list.get_child(i)
		texts.append(label.text)

	var joined := "\n".join(texts)
	assert_str(joined).contains("p1")
	assert_str(joined).contains("Money: 120")
	assert_str(joined).contains("Pos: 1")
	assert_str(joined).contains("ai-2")
	assert_str(joined).contains("Money: 300")
	assert_str(joined).contains("Pos: 4")
	assert_str(joined).contains("AI")
