extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_TURN_ADVANCED := "core.sanguo.game.turn.advanced"
const EVENT_HEALTH_UPDATED := "core.health.updated"
const EVENT_PLAYER_STATE_CHANGED := "core.sanguo.player.state.changed"
const EVENT_RANDOM_EVENT_APPLIED := "core.sanguo.random_event.applied"
const EVENT_BOSS_CHALLENGE_PROMPTED := "core.sanguo.boss.challenge.prompted"
const EVENT_GAME_ENDED := "core.sanguo.game.ended"

const SETTLEMENT_SCENE_PATH := "res://Game.Godot/Scenes/UI/SettlementScreen.tscn"
const WINNER_LABEL_PATH: NodePath = NodePath("Center/Panel/VBox/WinnerLabel")
const STATS_LABEL_PATH: NodePath = NodePath("Center/Panel/VBox/StatsSnapshotLabel")

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _assert_label_value(text: String, expected_value: String) -> void:
	assert_bool(text.ends_with(": " + expected_value)).is_true()

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var translated := String(TranslationServer.translate(key))
		if translated.strip_edges().length() > 0 and translated != key:
			return translated
	return ""

func _translate_summary(event_type: String) -> String:
	var summary_key := "ui.hud.event.%s.summary" % event_type
	var translated := _try_translate(summary_key)
	if translated.length() > 0:
		return translated
	return event_type

func _translate_field(event_type: String, section: String, field_key: String, fallback: String) -> String:
	var event_key := "ui.hud.event.%s.%s.%s" % [event_type, section, field_key]
	var text := _try_translate(event_key)
	if text.length() > 0:
		return text
	var shared_key := "ui.hud.event.shared.%s.%s" % [section, field_key]
	text = _try_translate(shared_key)
	if text.length() > 0:
		return text
	return fallback

func _instantiate_settlement_screen() -> Control:
	var packed = load(SETTLEMENT_SCENE_PATH)
	assert_object(packed).is_not_null()
	if packed == null:
		return null

	var scene: PackedScene = packed as PackedScene
	assert_object(scene).is_not_null()
	if scene == null:
		return null

	var node: Node = scene.instantiate()
	var screen: Control = node as Control
	assert_object(screen).is_not_null()
	if screen == null:
		return null

	add_child(auto_free(screen))
	return screen

func _publish_random_prompt_event() -> void:
	var payload := "{\"EventId\":\"event_money_small\",\"PickedId\":\"event_money_small\",\"EffectKind\":\"moneyDelta\",\"MoneyDelta\":5,\"StepDelta\":1,\"RngContextId\":\"rng.random_events:1:2:tile\",\"CandidatesSortedIdsHash\":\"deadbeef\",\"UiMessage\":\"Prompt from runtime event\"}"
	_bus.PublishSimple(EVENT_RANDOM_EVENT_APPLIED, "ut", payload)

# ACC:T177.1
# ACC:T177.3
func test_task177_runtime_hud_fields_follow_phase_timer_hp_reward_prompt_and_terminal_transitions() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()
	var date_label: Label = hud.get_node("TopBar/TopStack/HBox/DateLabel")
	var money_label: Label = hud.get_node("TopBar/TopStack/HBox/MoneyLabel")
	var hp_label: Label = hud.get_node("TopBar/TopStack/HBox/HealthLabel")
	var round_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/RoundValue")
	var pressure_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/BossPressureValue")
	var toast: Control = hud.get_node("EventToast")
	var toast_label: Label = hud.get_node("EventToast/Panel/Label")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")
	var details_label: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")

	_assert_label_value(money_label.text, "-")

	_bus.PublishSimple(EVENT_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1,\"TurnNumber\":1}")
	await get_tree().process_frame
	_assert_label_value(date_label.text, "0003-02-01")

	_bus.PublishSimple(EVENT_HEALTH_UPDATED, "ut", "{\"value\":88}")
	await get_tree().process_frame
	_assert_label_value(hp_label.text, "88")

	_bus.PublishSimple(EVENT_PLAYER_STATE_CHANGED, "ut", "{\"PlayerId\":\"p1\",\"Money\":120,\"PositionIndex\":0}")
	await get_tree().process_frame
	_assert_label_value(money_label.text, "120")

	# Negative path: reward display must not switch to a non-active player's payload.
	_bus.PublishSimple(EVENT_PLAYER_STATE_CHANGED, "ut", "{\"PlayerId\":\"p2\",\"Money\":999,\"PositionIndex\":0}")
	await get_tree().process_frame
	_assert_label_value(money_label.text, "120")

	_bus.PublishSimple(EVENT_BOSS_CHALLENGE_PROMPTED, "ut", "{\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":3,\"NextRoundPressureForecast\":2}")
	await get_tree().process_frame
	assert_str(round_label.text).contains("R3")
	assert_str(pressure_label.text).contains("+2")

	_publish_random_prompt_event()
	for _i in range(30):
		await get_tree().process_frame
		if toast.visible and toast_label.text.strip_edges().length() > 0:
			break
	assert_bool(toast.visible).is_true()
	assert_str(toast_label.text).contains(_translate_summary(EVENT_RANDOM_EVENT_APPLIED))
	assert_str(toast_label.text).contains("Prompt from runtime event")
	assert_str(details_label.text).contains(_translate_field(EVENT_RANDOM_EVENT_APPLIED, "delta", "money_delta", "money_delta"))
	assert_str(details_label.text).contains("+5")
	assert_str(details_label.text).contains(_translate_field(EVENT_RANDOM_EVENT_APPLIED, "delta", "step_delta", "step_delta"))
	assert_str(details_label.text).contains("+1")

	_bus.PublishSimple(EVENT_TURN_ADVANCED, "ut", "{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":2,\"Year\":3,\"Month\":2,\"Day\":2}")
	await get_tree().process_frame
	_assert_label_value(date_label.text, "0003-02-02")

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"WinnerPlayerId\":\"p1\",\"EndReason\":\"max_turns\"}")
	for _j in range(30):
		await get_tree().process_frame
		if log_list.get_item_count() > 0:
			var last := log_list.get_item_text(log_list.get_item_count() - 1)
			if last.find(_translate_summary(EVENT_GAME_ENDED)) >= 0:
				break

	assert_int(log_list.get_item_count()).is_greater(0)
	var terminal_summary := log_list.get_item_text(log_list.get_item_count() - 1)
	assert_str(terminal_summary).contains(_translate_summary(EVENT_GAME_ENDED))
	assert_str(terminal_summary).contains("p1")
	assert_str(details_label.text).contains(_translate_field(EVENT_GAME_ENDED, "detail", "winner_player_id", "winner_player_id"))
	assert_str(details_label.text).contains("p1")

	_restore_locale(original_locale)

# ACC:T177.3
func test_task177_outcome_surface_updates_winner_state_when_terminal_payload_changes() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	var winner_label: Label = screen.get_node_or_null(WINNER_LABEL_PATH) as Label
	var stats_label: RichTextLabel = screen.get_node_or_null(STATS_LABEL_PATH) as RichTextLabel
	assert_bool(winner_label != null).is_true()
	assert_bool(stats_label != null).is_true()
	if winner_label == null or stats_label == null:
		return

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"WinnerPlayerId\":\"p1\",\"EndReason\":\"max_turns\",\"StatsSnapshot\":{\"TurnNumber\":10,\"TreasuryMinorUnits\":0}}")
	await get_tree().process_frame
	assert_bool(screen.visible).is_true()
	assert_str(winner_label.text).is_equal("p1")
	assert_str(stats_label.text).contains("TurnNumber")

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"WinnerPlayerId\":\"p2\",\"EndReason\":\"boss_defeat\",\"StatsSnapshot\":{\"TurnNumber\":11,\"TreasuryMinorUnits\":123}}")
	await get_tree().process_frame
	assert_bool(screen.visible).is_true()
	assert_str(winner_label.text).is_equal("p2")
	assert_str(winner_label.text).is_not_equal("p1")
	assert_str(stats_label.text).contains("11")

# ACC:T177.3
func test_task177_outcome_surface_ignores_incomplete_or_malformed_terminal_payload() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	var winner_label: Label = screen.get_node_or_null(WINNER_LABEL_PATH) as Label
	var stats_label: RichTextLabel = screen.get_node_or_null(STATS_LABEL_PATH) as RichTextLabel
	assert_bool(winner_label != null).is_true()
	assert_bool(stats_label != null).is_true()
	if winner_label == null or stats_label == null:
		return

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"WinnerPlayerId\":\"p1\",\"EndReason\":\"max_turns\",\"StatsSnapshot\":{\"TurnNumber\":10,\"TreasuryMinorUnits\":0}}")
	await get_tree().process_frame
	assert_str(winner_label.text).is_equal("p1")
	assert_str(stats_label.text).contains("TurnNumber")
	assert_str(stats_label.text).contains("10")

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"EndReason\":\"max_turns\",\"StatsSnapshot\":{\"TurnNumber\":99,\"TreasuryMinorUnits\":999}}")
	await get_tree().process_frame
	assert_str(winner_label.text).is_equal("p1")
	assert_str(stats_label.text).contains("10")

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{")
	await get_tree().process_frame
	assert_str(winner_label.text).is_equal("p1")
	assert_str(stats_label.text).contains("10")
