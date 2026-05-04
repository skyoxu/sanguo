extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"
const REQUIRED_SCOPE_TASK_IDS := [
	68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90,
	94, 95, 96, 97, 98, 99, 100, 102, 103, 105, 107, 110, 111, 112, 113, 114, 115, 116, 117,
	118, 121, 122, 123, 124, 125, 127, 128, 129, 130, 132, 133, 135, 136, 138, 139, 140, 143,
	144, 145
]

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _wait_frames(frame_count: int = 2) -> void:
	for _i in range(frame_count):
		await get_tree().process_frame

func _publish_city_bought() -> void:
	_bus.PublishSimple(
		CITY_BOUGHT_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":100}"
	)

func _publish_turn_advanced(turn_number: int) -> void:
	_bus.PublishSimple(
		TURN_ADVANCED_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":%d,\"Year\":1,\"Month\":%d,\"Day\":1}" % [turn_number, turn_number]
	)

func _reset_hud_state(hud: Node) -> void:
	var panel: Control = hud.get_node("EventLogPanel")
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	panel.MaxEntries = 5
	log_list.clear()
	popup.visible = false
	popup_message.text = ""

func _read_hud_state(hud: Node) -> Dictionary:
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	return {
		"log_count": log_list.get_item_count(),
		"popup_visible": popup.visible,
		"popup_text": String(popup_message.text).strip_edges()
	}

func _spawn_detached_hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(hud)
	await get_tree().process_frame
	remove_child(hud)
	return hud

# ACC:T179.1
# ACC:T179.3
func test_real_hud_shows_updates_for_actions_and_invalid_feedback() -> void:
	var active_hud := await _hud()
	_reset_hud_state(active_hud)
	var toast_label: Label = active_hud.get_node("EventToast/Panel/Label")
	var popup: Control = active_hud.get_node("EventResultPopup")
	var popup_message: Label = active_hud.get_node("EventResultPopup/Center/Panel/VBox/Message")
	popup.visible = false
	popup_message.text = ""

	_publish_city_bought()
	await _wait_frames(2)
	_bus.PublishSimple(CITY_BOUGHT_TYPE, "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"\",\"CityId\":\"\",\"Price\":-1}")
	_bus.PublishSimple(CITY_BOUGHT_TYPE, "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\"")
	await _wait_frames(2)

	var active_state := _read_hud_state(active_hud)
	assert_bool(active_state["log_count"] > 0).is_true()
	assert_bool(String(toast_label.text).begins_with("i18n.")).is_false()
	assert_bool(popup.visible).is_true()
	assert_bool(String(popup_message.text).strip_edges().length() > 0).is_true()

# ACC:T179.2
func test_required_surfaces_present_in_real_hud_scene() -> void:
	var hud := await _hud()
	assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/MoneyLabel")).is_not_null() # ResourcePanel equivalent
	assert_object(hud.get_node_or_null("ActionPanel")).is_not_null() # BuildPanel equivalent
	assert_object(hud.get_node_or_null("TopBar/TopStack/CampaignParamsPanel")).is_not_null() # ProgressionPanel equivalent

# ACC:T179.4
# ACC:T179.6
func test_orphan_hud_remains_unchanged_after_detach_on_publish() -> void:
	var active_hud := await _hud()
	var orphan_hud := await _spawn_detached_hud()
	_reset_hud_state(active_hud)
	_reset_hud_state(orphan_hud)

	_publish_city_bought()
	_publish_turn_advanced(2)
	await _wait_frames(3)

	var active_state := _read_hud_state(active_hud)
	var orphan_state := _read_hud_state(orphan_hud)
	assert_int(active_state["log_count"]).is_equal(2)
	assert_bool(active_state["popup_visible"]).is_true()
	assert_int(orphan_state["log_count"]).is_equal(0)
	assert_bool(orphan_state["popup_visible"]).is_false()
	assert_str(orphan_state["popup_text"]).is_empty()

	if is_instance_valid(orphan_hud):
		orphan_hud.queue_free()
		await get_tree().process_frame

# ACC:T179.5
func test_missing_key_policy_uses_real_rendered_text_not_raw_key() -> void:
	var hud := await _hud()
	var toast_label: Label = hud.get_node("EventToast/Panel/Label")
	var raw_key := "economy.explain.upgrade"

	_publish_city_bought()
	await _wait_frames(2)
	assert_bool(String(toast_label.text).contains(raw_key)).is_false()

# ACC:T179.7
func test_scope_mapping_asserts_real_event_log_growth() -> void:
	var hud := await _hud()
	_reset_hud_state(hud)
	var mapping_text := FileAccess.get_file_as_string("res://../.taskmaster/tasks/tasks_back.json")

	for i in range(1, 6):
		_publish_turn_advanced(i)
		await _wait_frames(2)

	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	assert_int(log_list.get_item_count()).is_equal(5)
	for task_id in REQUIRED_SCOPE_TASK_IDS:
		assert_bool(mapping_text.contains("\"T%d\"" % task_id)).is_true()
