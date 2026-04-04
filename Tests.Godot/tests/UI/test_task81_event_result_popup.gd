extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _wait_for_log_items(log_list: ItemList, expected_min: int, max_frames: int = 20) -> void:
	for _i in range(max_frames):
		if log_list.get_item_count() >= expected_min:
			return
		await get_tree().process_frame

func _wait_for_popup_log_commit(popup: Control, message: Label, log_list: ItemList, max_frames: int = 30) -> void:
	for _i in range(max_frames):
		if log_list.get_item_count() > 0 and popup.visible and String(message.text).strip_edges().length() > 0:
			return
		await get_tree().process_frame

# ACC:T81.1
# RED-FIRST: A-008 split scope requires popup+log atomic commit on popup-capable domain events.
func test_task81_city_bought_commits_popup_and_log_atomically() -> void:
	var hud := await _hud()
	var popup: Control = hud.get_node("EventResultPopup")
	var message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	popup.visible = false
	message.text = ""
	log_list.clear()

	_bus.PublishSimple(
		CITY_BOUGHT_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":100}"
	)

	var committed := false
	for _i in range(30):
		await get_tree().process_frame
		var has_log := log_list.get_item_count() > 0
		var has_popup := popup.visible and String(message.text).strip_edges().length() > 0
		assert_bool(has_log == has_popup).is_true()
		if has_log and has_popup:
			committed = true
			break

	assert_bool(committed).is_true()
	assert_int(log_list.get_item_count()).is_equal(1)
	var summary := String(log_list.get_item_text(0)).strip_edges()
	var popup_text := String(message.text).strip_edges()
	assert_bool(summary.length() > 0).is_true()
	assert_bool(popup.visible).is_true()
	assert_bool(popup_text.length() > 0).is_true()
	assert_str(summary).not_contains(CITY_BOUGHT_TYPE)

# ACC:T81.2
# RED-FIRST: non-popup events may append log but must not mutate ResultPopup state.
func test_task81_non_result_event_does_not_mutate_popup_state() -> void:
	var hud := await _hud()
	var popup: Control = hud.get_node("EventResultPopup")
	var message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	popup.visible = false
	message.text = "sentinel"
	log_list.clear()

	_bus.PublishSimple(
		TURN_ADVANCED_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":2,\"Year\":3,\"Month\":2,\"Day\":2}"
	)

	for _i in range(20):
		await get_tree().process_frame
		assert_bool(popup.visible).is_false()
		assert_str(String(message.text)).is_equal("sentinel")
		if log_list.get_item_count() > 0:
			break

	assert_int(log_list.get_item_count()).is_equal(1)
	assert_bool(popup.visible).is_false()
	assert_str(String(message.text)).is_equal("sentinel")
