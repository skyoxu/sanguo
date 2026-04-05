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
# RED-FIRST: when event volume exceeds visible window, EventLogPanel must keep a deterministic bounded window.
func test_task82_event_log_windowing_keeps_bounded_visible_entries() -> void:
	var hud := await _hud()
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.MaxEntries = 5
	log_list.clear()

	for i in range(1, 9):
		_publish_turn_advanced(i, "p%d" % i)
		await _wait_frames(2)

	assert_int(log_list.get_item_count()).is_equal(5)

	for i in range(9, 13):
		_publish_turn_advanced(i, "p%d" % i)
		await _wait_frames(2)

	assert_int(log_list.get_item_count()).is_equal(5)

# ACC:T82.1
# RED-FIRST: lowering MaxEntries at runtime should trim already-rendered items immediately to the new window size.
func test_task82_runtime_max_entries_shrink_trims_existing_entries() -> void:
	var hud := await _hud()
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.MaxEntries = 10
	log_list.clear()

	for i in range(1, 9):
		_publish_turn_advanced(i, "p%d" % i)
		await _wait_frames(2)

	assert_int(log_list.get_item_count()).is_equal(8)

	event_log_panel.MaxEntries = 5
	await _wait_frames(1)
	assert_int(log_list.get_item_count()).is_equal(5)
