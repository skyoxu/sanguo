extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_OBJECTIVE_SKIPPED := "core.sanguo.objective.skipped"
const EVENT_UI_TILE_ACTION_SELECTED := "ui.sanguo.tile.action.selected"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _create_event_capture_sink() -> Dictionary:
	var sink := {
		"types": []
	}
	var callback := func(event_type, _source, _data_json, _id, _specversion, _content_type, _timestamp):
		var text := str(event_type)
		if sink["types"].size() < 256:
			sink["types"].append(text)
	_connect_domain_event_emitted(callback)
	sink["callback"] = callback
	return sink

func _count_event_type(sink: Dictionary, event_type: String) -> int:
	if not sink.has("types"):
		return 0
	var count := 0
	for item in sink["types"]:
		if str(item) == event_type:
			count += 1
	return count

func _count_buttons(node: Node) -> int:
	var count := 1 if node is Button else 0
	for child in node.get_children():
		count += _count_buttons(child)
	return count

func _wait_for_details_text(label: Label, expected: String, max_frames: int = 30) -> String:
	var text := str(label.text)
	for _i in range(max_frames):
		if text.contains(expected):
			return text
		await get_tree().process_frame
		text = str(label.text)
	return text

# acceptance: ACC:T199.1
# acceptance: ACC:T199.2
# acceptance: ACC:T199.3
# acceptance: ACC:T199.4
# acceptance: ACC:T199.5
func test_task199_operator_event_log_read_surface_exposes_state_without_mutation_controls() -> void:
	var event_sink := _create_event_capture_sink()
	var hud := await _hud()
	var read_surface: Control = hud.get_node("EventLogPanel")
	var details: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")
	var action_panel: Control = hud.get_node("ActionPanel")
	var skip_button: Button = hud.get_node("ActionPanel/VBox/SkipButton")

	read_surface.show()
	_bus.PublishSimple(EVENT_OBJECTIVE_SKIPPED, "operator-read-surface", "{\"GameId\":\"g199\",\"ObjectiveId\":\"obj-199\",\"RoundNumber\":9,\"Reason\":\"run_ended_in_boss\",\"BossId\":\"boss_yellow_turban\"}")
	var detail_text := await _wait_for_details_text(details, "obj-199")

	assert_bool(read_surface.visible).is_true()
	assert_str(detail_text).contains("obj-199")
	assert_str(detail_text).contains("BOSS")
	assert_str(detail_text).contains("boss_yellow_turban")
	assert_int(_count_buttons(read_surface)).is_equal(0)
	assert_bool(read_surface != action_panel).is_true()

	var before_skip_events := _count_event_type(event_sink, EVENT_UI_TILE_ACTION_SELECTED)
	skip_button.pressed.emit()
	await get_tree().process_frame
	var after_skip_events := _count_event_type(event_sink, EVENT_UI_TILE_ACTION_SELECTED)

	assert_int(after_skip_events).is_equal(before_skip_events)
	assert_str(details.text).contains("obj-199")
