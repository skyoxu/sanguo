extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const OBJECTIVE_SKIPPED_TYPE := "core.sanguo.objective.skipped"
const LOCALE_ZH := "zh"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _publish_objective_skipped(payload_json: String) -> void:
	_bus.PublishSimple(OBJECTIVE_SKIPPED_TYPE, "ut", payload_json)

func _toast_visible(hud: Node) -> bool:
	var toast: Control = hud.get_node("EventToast")
	return bool(toast.visible)

func _toast_text(hud: Node) -> String:
	var label: Label = hud.get_node("EventToast/Panel/Label")
	return str(label.text)

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

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

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var translated := String(TranslationServer.translate(key))
		if translated.strip_edges().length() > 0 and translated != key:
			return translated
	return ""

func _require_translation(key: String) -> String:
	var translated := _try_translate(key)
	assert_bool(translated.strip_edges().length() > 0).is_true()
	return translated

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
	var normalized := _normalize_token(token)
	var key := "ui.hud.event.shared.detail.%s.%s" % [category, normalized]
	var translated := _try_translate(key)
	return translated if translated.length() > 0 else token

func _await_hud_event(hud: Node, max_frames: int = 30) -> Dictionary:
	var toast_text := ""
	var items: Array = []
	for _i in range(max_frames):
		toast_text = _toast_text(hud).strip_edges()
		items = _event_log_messages(hud)
		if _toast_visible(hud) and toast_text.length() > 0 and items.size() > 0:
			return {
				"toast": toast_text,
				"items": items,
			}
		await get_tree().process_frame
	return {
		"toast": toast_text,
		"items": items,
	}

func _objective_skipped_payload(reason: String = "run_ended_in_boss") -> String:
	return JSON.stringify({
		"GameId": "g-task77",
		"ObjectiveId": "obj_task77_round6",
		"RoundNumber": 6,
		"Reason": reason,
		"BossId": "boss_1",
		"OccurredAt": "2026-01-01T00:00:00Z",
		"CorrelationId": "corr-task77",
		"CausationId": "ut.task77",
	})

func _read_task_view(task_view_file: String) -> Dictionary:
	var repo_root := ProjectSettings.globalize_path("res://../")
	var task_view_path := repo_root.path_join(".taskmaster/tasks/%s" % task_view_file)
	assert_bool(FileAccess.file_exists(task_view_path)).is_true()
	var task_view_text := FileAccess.get_file_as_string(task_view_path)
	var parsed = JSON.parse_string(task_view_text)
	assert_bool(typeof(parsed) == TYPE_ARRAY).is_true()
	return {
		"task_view_path": task_view_path,
		"tasks": parsed,
	}

func _find_task_by_taskmaster_id(tasks: Array, taskmaster_id: int) -> Dictionary:
	for item in tasks:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var dict: Dictionary = item
		if int(dict.get("taskmaster_id", -1)) == taskmaster_id:
			return dict
	return {}

# ACC:T77.2
func test_task77_accepts_when_task118_evidence_is_present_and_ui_explain_chain_passes() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud := await _hud()
	var task_view := _read_task_view("tasks_gameplay.json")
	var tasks: Array = task_view.get("tasks", [])
	var task118 := _find_task_by_taskmaster_id(tasks, 118)
	var task77 := _find_task_by_taskmaster_id(tasks, 77)

	assert_bool(not task118.is_empty()).is_true()
	assert_bool(not task77.is_empty()).is_true()
	var task118_refs: Array = task118.get("test_refs", [])
	var task77_acceptance: Array = task77.get("acceptance", [])

	assert_bool(task118_refs.has("Game.Core.Tests/Tasks/Task118V3Tests.cs")).is_true()
	assert_bool(task77_acceptance.size() >= 2).is_true()
	assert_bool(str(task77_acceptance[1]).find("task 118") >= 0).is_true()
	assert_bool(str(task77_acceptance[1]).find("UI/explain-chain") >= 0).is_true()

	_publish_objective_skipped(_objective_skipped_payload())
	var event_result := await _await_hud_event(hud)
	var toast_text := str(event_result.get("toast", ""))
	var items: Array = event_result.get("items", [])

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(toast_text).is_not_empty()
	assert_int(items.size()).is_greater_equal(1)
	assert_str(str(items[items.size() - 1])).is_equal(toast_text)

	var summary_label := _require_translation("ui.hud.event.core.sanguo.objective.skipped.summary")
	var reason_label := _translate_field(OBJECTIVE_SKIPPED_TYPE, "detail", "reason", "reason")
	var reason_value := _translate_token("objective_skip_reason", "run_ended_in_boss")
	var round_label := _translate_field(OBJECTIVE_SKIPPED_TYPE, "detail", "trigger_round", "round")

	assert_str(toast_text).contains(summary_label)
	assert_str(toast_text).contains(reason_label + "=" + reason_value)
	assert_str(toast_text).contains(round_label + "=6")
	assert_str(toast_text).not_contains("core.sanguo.objective.skipped")
	assert_str(toast_text).not_contains("reason=")
	assert_str(toast_text).not_contains("run_ended_in_boss")

	_restore_locale(original_locale)

# ACC:T77.2
func test_task77_refuses_acceptance_when_task118_explain_chain_fails_even_if_hud_requests_visibility() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud := await _hud()

	_publish_objective_skipped("{bad-json")
	for _i in range(12):
		await get_tree().process_frame

	var toast_text := _toast_text(hud).strip_edges()
	var items := _event_log_messages(hud)

	assert_bool(_toast_visible(hud)).is_false()
	assert_str(toast_text).is_empty()
	assert_int(items.size()).is_equal(0)

	_restore_locale(original_locale)
