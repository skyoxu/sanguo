extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_GAME_STARTED := "core.sanguo.game.started"
const EVENT_PLAYER_STATE_CHANGED := "core.sanguo.player.state.changed"
const EVENT_BOSS_CHALLENGE_PROMPTED := "core.sanguo.boss.challenge.prompted"
const EVENT_COMBAT_STARTED := "core.sanguo.combat.started"
const EVENT_COMBAT_ENDED := "core.sanguo.combat.ended"
const EVENT_OBJECTIVE_SKIPPED := "core.sanguo.objective.skipped"
const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_TOKEN_MOVED := "core.sanguo.board.token.moved"
const EVENT_UI_TILE_ACTION_SELECTED := "ui.sanguo.tile.action.selected"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _toast_visible(hud: Node) -> bool:
	var toast: Control = hud.get_node("EventToast")
	return bool(toast.visible)

func _toast_text(hud: Node) -> String:
	var label: Label = hud.get_node("EventToast/Panel/Label")
	return str(label.text)

func _event_list(hud: Node) -> ItemList:
	return hud.get_node("EventLogPanel/Margin/VBox/EventList") as ItemList

func _event_log_messages(hud: Node) -> Array:
	var list := _event_list(hud)
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

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

func _find_action_button(actions_box: Node, action_id: String) -> Button:
	var normalized := action_id.strip_edges().to_lower()
	if normalized.length() == 0:
		return null
	var candidates: Array[String] = [normalized]
	if TranslationServer.has_method("translate"):
		var key := "ui.hud.action.%s" % normalized
		var translated := String(TranslationServer.translate(key)).strip_edges()
		if translated.length() > 0 and translated != key:
			candidates.append(translated)
	for child in actions_box.get_children():
		if not (child is Button):
			continue
		var button_text := str((child as Button).text).strip_edges().to_lower()
		for candidate in candidates:
			if button_text == String(candidate).to_lower():
				return child as Button
	return null

func _details_text(hud: Node) -> String:
	var label: Label = hud.get_node("EventLogPanel/Margin/VBox/Details/Scroll/DetailsText")
	return str(label.text)

func _wait_for_log_items(hud: Node, min_count: int, max_frames: int = 30) -> Array:
	var items := _event_log_messages(hud)
	for _i in range(max_frames):
		if items.size() >= min_count:
			return items
		await get_tree().process_frame
		items = _event_log_messages(hud)
	return items

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
	var translated := _try_translate(event_key)
	if translated.length() > 0:
		return translated
	var shared_key := "ui.hud.event.shared.%s.%s" % [section, field_key]
	translated = _try_translate(shared_key)
	if translated.length() > 0:
		return translated
	return fallback

func _normalize_token(token: String) -> String:
	var result := ""
	for i in range(token.length()):
		var ch := token[i]
		if ch == "-" or ch == " ":
			if not result.ends_with("_"):
				result += "_"
		elif ch >= "A" and ch <= "Z":
			if result.length() > 0 and not result.ends_with("_"):
				result += "_"
			result += String(ch).to_lower()
		else:
			result += String(ch).to_lower()
	return result

func _translate_token(category: String, token: String) -> String:
	var key := "ui.hud.event.shared.detail.%s.%s" % [category, _normalize_token(token)]
	var translated := _try_translate(key)
	return translated if translated.length() > 0 else token

func _set_locale(locale: String) -> String:
	var original := ""
	if TranslationServer.has_method("get_locale"):
		original = String(TranslationServer.get_locale())
	if TranslationServer.has_method("set_locale") and locale.strip_edges().length() > 0:
		TranslationServer.set_locale(locale)
	return original

func _restore_locale(original: String) -> void:
	if TranslationServer.has_method("set_locale") and original.strip_edges().length() > 0:
		TranslationServer.set_locale(original)

# ACC:T178.3
# ACC:T212.1
# ACC:T212.2
# ACC:T212.5
func test_task178_runtime_combat_events_render_pressure_targeting_outcome_and_feedback() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()
	var pressure_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/BossPressureValue")

	_bus.PublishSimple(EVENT_BOSS_CHALLENGE_PROMPTED, "ut", "{\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":6,\"WinRateTier\":\"mid\",\"NextRoundPressureForecast\":4,\"KeyLossSummary\":\"camp_hp_risk\",\"FailConsequence\":\"return_to_camp_end_round\"}")
	_bus.PublishSimple(EVENT_COMBAT_STARTED, "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EncounterId\":\"enc-178\",\"RandomSeed\":42}")
	_bus.PublishSimple(EVENT_COMBAT_ENDED, "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EncounterId\":\"enc-178\",\"Result\":{\"Outcome\":\"win\",\"MoneyDelta\":12,\"EncounterTarget\":2,\"EffectiveCombatRating\":7}}")
	var items := await _wait_for_log_items(hud, 3)

	assert_int(items.size()).is_greater_equal(3)
	assert_str(pressure_label.text).contains("+4")

	var joined := "\n".join(items)
	assert_str(joined).contains(_translate_summary(EVENT_BOSS_CHALLENGE_PROMPTED))
	assert_str(joined).contains(_translate_summary(EVENT_COMBAT_STARTED))
	assert_str(joined).contains(_translate_summary(EVENT_COMBAT_ENDED))

	var pressure_key := _translate_field(EVENT_BOSS_CHALLENGE_PROMPTED, "detail", "next_round_pressure_forecast", "next_round_pressure_forecast")
	var fail_key := _translate_field(EVENT_BOSS_CHALLENGE_PROMPTED, "detail", "fail_consequence", "fail_consequence")
	var fail_value := _translate_token("fail_consequence", "return_to_camp_end_round")
	assert_str(joined).contains(pressure_key + "=4")
	assert_str(joined).contains(fail_key + "=" + fail_value)

	var details := _details_text(hud)
	var target_key := _translate_field(EVENT_COMBAT_ENDED, "detail", "encounter_target", "encounter_target")
	var rating_key := _translate_field(EVENT_COMBAT_ENDED, "detail", "effective_combat_rating", "effective_combat_rating")
	var outcome_key := _translate_field(EVENT_COMBAT_ENDED, "detail", "outcome", "outcome")
	var outcome_value := _translate_token("outcome", "win")
	assert_str(details).contains(target_key)
	assert_str(details).contains("2")
	assert_str(details).contains(rating_key)
	assert_str(details).contains("7")
	assert_str(details).contains(outcome_key)
	assert_str(details).contains(outcome_value)

	_restore_locale(original_locale)

# ACC:T178.4
# ACC:T212.2
# ACC:T212.3
func test_task178_empty_state_keeps_no_active_pressure_without_combat_data() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()
	var pressure_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/BossPressureValue")

	assert_str(pressure_label.text).contains("No boss pressure")

	_bus.PublishSimple(EVENT_GAME_STARTED, "ut", "{\"game_start_config\":{\"run_mode\":\"campaign\",\"commander_id\":\"c_liu_bei\",\"difficulty\":\"normal\"}}")
	_bus.PublishSimple(EVENT_PLAYER_STATE_CHANGED, "ut", "{\"PlayerId\":\"p1\",\"Money\":120,\"PositionIndex\":0}")
	await get_tree().process_frame

	assert_str(pressure_label.text).contains("No boss pressure")
	var items := _event_log_messages(hud)
	var joined := "\n".join(items)
	assert_str(joined).not_contains(_translate_summary(EVENT_COMBAT_STARTED))
	assert_str(joined).not_contains(_translate_summary(EVENT_COMBAT_ENDED))

	_restore_locale(original_locale)

# ACC:T178.5
# ACC:T212.1
# ACC:T212.2
# ACC:T212.4
# ACC:T212.5
func test_task178_invalid_or_blocked_combat_state_shows_explicit_feedback_instead_of_silent() -> void:
	var original_locale := _set_locale("en")
	var event_sink := _create_event_capture_sink()
	var hud := await _hud()
	var pressure_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/BossPressureValue")
	var action_panel: Control = hud.get_node("ActionPanel")
	var actions_box: VBoxContainer = hud.get_node("ActionPanel/VBox/Actions")
	var dice_button: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")
	var skip_button: Button = hud.get_node("ActionPanel/VBox/SkipButton")

	_bus.PublishSimple(EVENT_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
	await get_tree().process_frame
	_bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"TurnNumber\":1,\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":0,\"OccurredAt\":\"2026-01-01T00:00:00Z\",\"CorrelationId\":\"corr-178\",\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":2}}")
	await get_tree().process_frame
	_bus.PublishSimple(EVENT_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":0,\"Steps\":0,\"PassedStart\":false,\"CorrelationId\":\"corr-178-open\"}")
	await get_tree().process_frame
	var build_btn := _find_action_button(actions_box, "build")
	assert_object(build_btn).is_not_null()
	assert_bool(action_panel.visible).is_true()
	assert_bool(dice_button.disabled).is_true()
	if build_btn != null:
		build_btn.pressed.emit()
		await get_tree().process_frame
	assert_bool(action_panel.visible).is_false()
	assert_bool(dice_button.disabled).is_true()

	_bus.PublishSimple(EVENT_OBJECTIVE_SKIPPED, "ut", "{\"GameId\":\"g1\",\"ObjectiveId\":\"obj-178\",\"RoundNumber\":6,\"Reason\":\"run_ended_in_boss\",\"BossId\":\"boss_yellow_turban\"}")
	var first_items := await _wait_for_log_items(hud, 1)
	var toast_text := _toast_text(hud).strip_edges()

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(toast_text).is_not_empty()
	assert_int(first_items.size()).is_greater_equal(1)
	assert_str(first_items[first_items.size() - 1]).is_equal(toast_text)

	var reason_key := _translate_field(EVENT_OBJECTIVE_SKIPPED, "detail", "reason", "reason")
	var reason_value := _translate_token("objective_skip_reason", "run_ended_in_boss")
	var affected_surface_key := _translate_field(EVENT_OBJECTIVE_SKIPPED, "detail", "affected_surface", "affected_surface")
	var affected_surface_value := _translate_token("affected_surface", "combat_hud_pressure_camera_feedback")
	var next_step_key := _translate_field(EVENT_OBJECTIVE_SKIPPED, "detail", "next_step", "next_step")
	var next_step_value := _translate_field(EVENT_OBJECTIVE_SKIPPED, "detail", "next_step.continue", "continue")
	assert_str(toast_text).contains(_translate_summary(EVENT_OBJECTIVE_SKIPPED))
	assert_str(toast_text).contains(reason_key + "=" + reason_value)
	assert_str(toast_text).contains(affected_surface_key + "=" + affected_surface_value)
	assert_str(toast_text).contains(next_step_key + "=" + next_step_value)
	assert_bool(action_panel.visible).is_false()
	assert_bool(dice_button.disabled).is_true()
	var before_skip_events := _count_event_type(event_sink, EVENT_UI_TILE_ACTION_SELECTED)
	skip_button.pressed.emit()
	await get_tree().process_frame
	var after_skip_events := _count_event_type(event_sink, EVENT_UI_TILE_ACTION_SELECTED)
	assert_int(after_skip_events).is_equal(before_skip_events)
	assert_str(pressure_label.text).contains("R6")
	assert_str(pressure_label.text).contains("+0")
	var first_details := _details_text(hud)
	assert_str(first_details).contains(affected_surface_key + ": " + affected_surface_value)
	assert_str(first_details).contains(next_step_key + ": " + next_step_value)

	var before_invalid := first_items.size()
	_bus.PublishSimple(EVENT_OBJECTIVE_SKIPPED, "ut", "{\"GameId\":\"g1\",\"ObjectiveId\":\"obj-178-invalid\",\"RoundNumber\":7,\"BossId\":\"boss_yellow_turban\"}")
	var second_items := await _wait_for_log_items(hud, before_invalid + 1)

	assert_int(second_items.size()).is_equal(before_invalid + 1)
	var second_line := str(second_items[second_items.size() - 1])
	assert_str(second_line).contains(_translate_summary(EVENT_OBJECTIVE_SKIPPED))
	assert_str(second_line).contains(affected_surface_key + "=" + affected_surface_value)
	assert_str(second_line).contains(next_step_key + "=" + next_step_value)

	_restore_locale(original_locale)

# ACC:T178.9
# ACC:T212.2
# ACC:T212.3
func test_task178_camera_feedback_resets_to_neutral_when_pressure_signal_is_cleared() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()
	var pressure_label: Label = hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/BossPressureValue")
	var action_panel: Control = hud.get_node("ActionPanel")
	var actions_box: VBoxContainer = hud.get_node("ActionPanel/VBox/Actions")
	var dice_button: Button = hud.get_node("TopBar/TopStack/HBox/DiceButton")

	_bus.PublishSimple(EVENT_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
	await get_tree().process_frame
	_bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"TurnNumber\":1,\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":0,\"OccurredAt\":\"2026-01-01T00:00:00Z\",\"CorrelationId\":\"corr-178-r9\",\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":2}}")
	await get_tree().process_frame
	_bus.PublishSimple(EVENT_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":0,\"Steps\":0,\"PassedStart\":false,\"CorrelationId\":\"corr-178-r9-open\"}")
	await get_tree().process_frame
	assert_bool(action_panel.visible).is_true()
	assert_bool(dice_button.disabled).is_true()
	var build_btn := _find_action_button(actions_box, "build")
	assert_object(build_btn).is_not_null()
	if build_btn != null:
		build_btn.pressed.emit()
		await get_tree().process_frame
	assert_bool(action_panel.visible).is_false()
	assert_bool(dice_button.disabled).is_true()

	_bus.PublishSimple(EVENT_BOSS_CHALLENGE_PROMPTED, "ut", "{\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":8,\"NextRoundPressureForecast\":3}")
	await get_tree().process_frame

	assert_str(pressure_label.text).contains("R8")
	assert_str(pressure_label.text).contains("+3")

	_bus.PublishSimple(EVENT_OBJECTIVE_SKIPPED, "ut", "{\"GameId\":\"g1\",\"ObjectiveId\":\"obj-178-reset\",\"RoundNumber\":8,\"Reason\":\"run_ended_in_boss\",\"BossId\":\"boss_yellow_turban\"}")
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_false()
	assert_bool(dice_button.disabled).is_true()
	assert_str(pressure_label.text).contains("R8")
	assert_str(pressure_label.text).contains("+0")

	_bus.PublishSimple(EVENT_GAME_STARTED, "ut", "{\"game_start_config\":{\"run_mode\":\"campaign\",\"commander_id\":\"c_liu_bei\",\"difficulty\":\"normal\"}}")
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_false()
	assert_bool(dice_button.disabled).is_true()
	assert_str(pressure_label.text).contains("No boss pressure")
	assert_str(pressure_label.text).not_contains("+3")

	_restore_locale(original_locale)
