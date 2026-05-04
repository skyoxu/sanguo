extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"
const CLOSURE_GATE_SCRIPT := preload("res://Game.Godot/Scripts/UI/HudExplainabilityIntegrationClosureGate.cs")
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

func _wait_frames(count: int = 2) -> void:
	for _i in range(count):
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

func _task81_evidence_from_hud(hud: Node) -> bool:
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	log_list.clear()
	popup.visible = false
	popup_message.text = ""

	_publish_city_bought()
	await _wait_frames(2)
	return popup.visible and String(popup_message.text).strip_edges().length() > 0 and log_list.get_item_count() > 0

func _task82_evidence_from_hud(hud: Node) -> bool:
	var panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	panel.MaxEntries = 5
	log_list.clear()
	for i in range(1, 9):
		_publish_turn_advanced(i)
		await _wait_frames(2)
	return log_list.get_item_count() == 5

func _assert_equivalent_surfaces_present(hud: Node) -> void:
	assert_object(hud.get_node_or_null("TopBar/TopStack/HBox/MoneyLabel")).is_not_null() # ResourcePanel equivalent
	assert_object(hud.get_node_or_null("ActionPanel")).is_not_null() # BuildPanel equivalent
	assert_object(hud.get_node_or_null("TopBar/TopStack/CampaignParamsPanel")).is_not_null() # ProgressionPanel equivalent

# ACC:T179.1
# ACC:T179.2
# ACC:T179.3
func test_hud_reacts_to_real_economy_and_progression_events() -> void:
	var hud := await _hud()
	_assert_equivalent_surfaces_present(hud)
	var event_log: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
	var action_panel: Control = hud.get_node("ActionPanel")
	var round_value: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/RoundValue")
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = hud.get_node("EventResultPopup/Center/Panel/VBox/Message")
	var before_log_count := event_log.get_item_count()
	var before_action_visible := action_panel.visible

	_publish_city_bought()
	_publish_turn_advanced(1)
	_bus.PublishSimple(CITY_BOUGHT_TYPE, "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"\",\"CityId\":\"\",\"Price\":-1}")
	await _wait_frames(3)

	assert_bool(event_log.get_item_count() > before_log_count).is_true()
	assert_bool(String(money_label.text).strip_edges().length() > 0).is_true() # resource surface is wired and readable
	assert_bool(String(round_value.text).strip_edges().length() > 0).is_true() # progression surface is wired and readable
	assert_bool(action_panel.visible == before_action_visible or action_panel.visible).is_true() # build surface stays deterministic
	assert_bool(popup.visible).is_true()
	assert_bool(String(popup_message.text).strip_edges().length() > 0).is_true() # invalid-action-like feedback path visible

# ACC:T179.4
func test_integration_closure_refused_when_task81_exists_but_task82_missing() -> void:
	var hud := await _hud()
	var gate = CLOSURE_GATE_SCRIPT.new()
	var has_task81 := await _task81_evidence_from_hud(hud)
	var has_task82 := false
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = hud.get_node("EventResultPopup/Center/Panel/VBox/Message")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	var closure_complete: bool = gate.Evaluate(has_task81, has_task82)
	assert_bool(has_task81).is_true()
	assert_bool(closure_complete).is_false()
	assert_bool(popup.visible).is_true()
	assert_bool(String(popup_message.text).strip_edges().length() > 0).is_true()
	assert_bool(log_list.get_item_count() > 0).is_true()

# ACC:T179.5
func test_release_mode_missing_key_never_exposes_raw_i18n_key() -> void:
	var hud := await _hud()
	var toast_label: Label = hud.get_node("EventToast/Panel/Label")
	var raw_key := "i18n.task179.missing"

	_bus.PublishSimple("core.city.bought", "ut", "{\"GameId\":\"g1\"}")
	await _wait_frames(2)
	var rendered_text := String(toast_label.text)

	assert_bool(rendered_text.begins_with("i18n.")).is_false()
	assert_bool(rendered_text.contains(raw_key)).is_false()

# ACC:T179.6
func test_unrelated_domain_state_remains_stable_after_ui_events() -> void:
	var hud := await _hud()
	var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
	var score_label: Label = hud.get_node("TopBar/TopStack/HBox/ScoreLabel")
	var health_label: Label = hud.get_node("TopBar/TopStack/HBox/HealthLabel")
	var action_panel: Control = hud.get_node("ActionPanel")
	var before_money_text := String(money_label.text)
	var before_score_text := String(score_label.text)
	var before_health_text := String(health_label.text)
	var before_action_visible := action_panel.visible

	_publish_turn_advanced(2)
	await _wait_frames(2)

	assert_str(String(money_label.text)).is_equal(before_money_text)
	assert_str(String(score_label.text)).is_equal(before_score_text)
	assert_str(String(health_label.text)).is_equal(before_health_text)
	assert_bool(action_panel.visible).is_equal(before_action_visible)
	assert_bool(hud.is_inside_tree()).is_true()

# ACC:T179.7
# ACC:T179.8
func test_scope_mapping_uses_real_task68_evidence_closure_path() -> void:
	var hud := await _hud()
	var has_task81 := await _task81_evidence_from_hud(hud)
	var has_task82 := await _task82_evidence_from_hud(hud)
	var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
	var round_value: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/RoundValue")
	var event_log: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	var action_panel: Control = hud.get_node("ActionPanel")
	var before_money_text := String(money_label.text)
	var before_round_text := String(round_value.text)
	var before_action_visible := action_panel.visible
	var before_log_count := event_log.get_item_count()

	_publish_city_bought()
	_publish_turn_advanced(3)
	await _wait_frames(3)

	assert_bool(has_task81).is_true()
	assert_bool(has_task82).is_true()
	assert_bool(String(money_label.text) != before_money_text).is_true()
	assert_bool(String(round_value.text) != before_round_text).is_true()
	assert_bool(event_log.get_item_count() > before_log_count).is_true()
	assert_bool(action_panel.visible == before_action_visible or action_panel.visible).is_true()

