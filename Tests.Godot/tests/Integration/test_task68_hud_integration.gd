extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"
const MAX_ENTRIES := 5
const CLOSURE_GATE_SCRIPT := preload("res://Game.Godot/Scripts/UI/HudExplainabilityIntegrationClosureGate.cs")

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

func _task81_evidence_from_hud(hud: Node) -> bool:
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	log_list.clear()
	popup.visible = false
	popup_message.text = ""

	_publish_city_bought()
	await _wait_frames(2)

	var has_popup := popup.visible and String(popup_message.text).strip_edges().length() > 0
	var has_log := log_list.get_item_count() > 0
	return has_popup and has_log

func _task82_evidence_from_hud(hud: Node) -> bool:
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.MaxEntries = MAX_ENTRIES
	log_list.clear()

	for i in range(1, 9):
		_publish_turn_advanced(i)
		await _wait_frames(2)

	return log_list.get_item_count() == MAX_ENTRIES

# ACC:T68.1
func test_refuses_closure_when_only_task81_evidence_exists() -> void:
	var hud := await _hud()
	var closure_gate = CLOSURE_GATE_SCRIPT.new()

	var has_task81 := await _task81_evidence_from_hud(hud)
	var has_task82 := false
	var closure_complete: bool = closure_gate.Evaluate(has_task81, has_task82)

	assert_bool(has_task81).is_true()
	assert_bool(has_task82).is_false()
	assert_bool(closure_complete).is_false()

# ACC:T68.2
func test_refuses_closure_when_only_task82_evidence_exists() -> void:
	var hud := await _hud()
	var closure_gate = CLOSURE_GATE_SCRIPT.new()

	var has_task81 := false
	var has_task82 := await _task82_evidence_from_hud(hud)
	var closure_complete: bool = closure_gate.Evaluate(has_task81, has_task82)

	assert_bool(has_task81).is_false()
	assert_bool(has_task82).is_true()
	assert_bool(closure_complete).is_false()

# ACC:T68.3
func test_closes_integration_when_task81_and_task82_evidence_exist() -> void:
	var hud := await _hud()
	var closure_gate = CLOSURE_GATE_SCRIPT.new()

	var has_task81 := await _task81_evidence_from_hud(hud)
	var has_task82 := await _task82_evidence_from_hud(hud)
	var closure_complete: bool = closure_gate.Evaluate(has_task81, has_task82)

	assert_bool(has_task81).is_true()
	assert_bool(has_task82).is_true()
	assert_bool(closure_complete).is_true()
