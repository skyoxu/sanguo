extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

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

func _wait_frames(frame_count: int = 2) -> void:
	for _i in range(frame_count):
		await get_tree().process_frame

func _read_hud_state(hud: Node) -> Dictionary:
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	return {
		"log_count": log_list.get_item_count(),
		"popup_visible": popup.visible,
		"popup_text": String(popup_message.text).strip_edges()
	}

func _reset_hud_state(hud: Node) -> void:
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.MaxEntries = 5
	log_list.clear()
	popup.visible = false
	popup_message.text = ""

func _spawn_detached_hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(hud)
	await get_tree().process_frame
	remove_child(hud)
	return hud

func test_split_task_evidence_is_merged_before_hud_update() -> void:
	var hud := await _hud()
	_reset_hud_state(hud)

	_publish_city_bought()
	await _wait_frames(2)
	_publish_turn_advanced(1)
	await _wait_frames(2)

	var state := _read_hud_state(hud)
	assert_int(state["log_count"]).is_equal(2)
	assert_bool(state["popup_visible"]).is_true()
	assert_bool(String(state["popup_text"]).length() > 0).is_true()

# ACC:T68.4
# Negative path: an orphan/detached HUD must stay unchanged after publish.
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
	assert_bool(String(active_state["popup_text"]).length() > 0).is_true()

	assert_int(orphan_state["log_count"]).is_equal(0)
	assert_bool(orphan_state["popup_visible"]).is_false()
	assert_str(orphan_state["popup_text"]).is_empty()

	if is_instance_valid(orphan_hud):
		orphan_hud.queue_free()
		await get_tree().process_frame
