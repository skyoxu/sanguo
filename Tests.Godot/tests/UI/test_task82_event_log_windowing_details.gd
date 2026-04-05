extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _publish_turn_advanced(turn_number: int, player_id: String) -> void:
	_bus.PublishSimple(
		TURN_ADVANCED_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"ActivePlayerId\":\"%s\",\"TurnNumber\":%d,\"Year\":1,\"Month\":%d,\"Day\":1}" % [player_id, turn_number, turn_number]
	)

func _wait_frames(frame_count: int = 2) -> void:
	for _i in range(frame_count):
		await get_tree().process_frame

# ACC:T82.1
# RED-FIRST: latest entries must remain observable through panel selection after windowing truncates older entries.
func test_task82_event_log_windowing_keeps_latest_entries_observable() -> void:
	var hud := await _hud()
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	var details: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")

	event_log_panel.MaxEntries = 5
	log_list.clear()
	details.text = ""

	for i in range(1, 9):
		_publish_turn_advanced(i, "p%d" % i)
		await _wait_frames(2)

	assert_int(log_list.get_item_count()).is_equal(5)
	assert_str(str(details.text)).contains("p8")

	log_list.select(0)
	log_list.emit_signal("item_selected", 0)
	await _wait_frames(1)
	assert_str(str(details.text)).contains("p4")

	log_list.select(4)
	log_list.emit_signal("item_selected", 4)
	await _wait_frames(1)
	assert_str(str(details.text)).contains("p8")
