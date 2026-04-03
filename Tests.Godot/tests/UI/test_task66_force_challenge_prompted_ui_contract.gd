extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE := "core.sanguo.boss.challenge.prompted"
const LOCALE_ZH := "zh"
const LOCALE_MISSING := "zz-ZZ-task66"

var _bus: Node

func before() -> void:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _hud() -> Node:
	var hud := preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _publish_boss_challenge_prompted(payload: Dictionary) -> void:
	_bus.PublishSimple(EVENT_TYPE, "ut", JSON.stringify(payload))

func _boss_prompt_payload() -> Dictionary:
	return {
		"GameId": "g1",
		"BossId": "boss_1",
		"RoundNumber": 6,
		"WinRateTier": "mid",
		"NextRoundPressureForecast": 4,
		"KeyLossSummary": "camp_hp_risk",
		"FailConsequence": "return_to_camp_end_round",
	}

func _toast_visible(hud: Node) -> bool:
	var toast: Control = hud.get_node("EventToast")
	return bool(toast.visible)

func _toast_label_text(hud: Node) -> String:
	var toast: Control = hud.get_node("EventToast")
	var label: Label = toast.get_node("Panel/Label")
	return str(label.text)

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

func _await_event_summary(hud: Node, max_frames: int = 20) -> String:
	for _i in range(max_frames):
		var text := _toast_label_text(hud).strip_edges()
		if _toast_visible(hud) and text.length() > 0:
			return text
		await get_tree().process_frame
	return _toast_label_text(hud).strip_edges()

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

# ACC:T66.1
# Summary-only UI contract: publishing the boss challenge prompt must surface a visible
# UI summary that is consistent between the toast and event log and stays aligned to contract fields.
func test_task66_a006_boss_challenge_prompt_summary_is_visible_and_contract_aligned() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud := await _hud()

	_publish_boss_challenge_prompted(_boss_prompt_payload())
	var summary := await _await_event_summary(hud)
	var items := _event_log_messages(hud)

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(summary).is_not_empty()
	assert_int(items.size()).is_greater_equal(1)
	assert_str(str(items[items.size() - 1])).is_equal(summary)

	var summary_label := _require_translation("ui.hud.event.core.sanguo.boss.challenge.prompted.summary")
	var boss_label := _translate_field(EVENT_TYPE, "detail", "boss_id", "boss_id")
	var win_rate_label := _translate_field(EVENT_TYPE, "detail", "win_rate_tier", "win_rate_tier")
	var pressure_label := _translate_field(EVENT_TYPE, "detail", "next_round_pressure_forecast", "next_round_pressure_forecast")
	var fail_label := _translate_field(EVENT_TYPE, "detail", "fail_consequence", "fail_consequence")
	var loss_label := _translate_field(EVENT_TYPE, "detail", "key_loss_summary", "key_loss_summary")
	var round_label := _translate_field(EVENT_TYPE, "detail", "trigger_round", "round")

	assert_str(summary).contains(summary_label)
	assert_str(summary).contains(boss_label + "=boss_1")
	assert_str(summary).contains(win_rate_label + "=" + _translate_token("win_rate_tier", "mid"))
	assert_str(summary).contains(pressure_label + "=4")
	assert_str(summary).contains(fail_label + "=" + _translate_token("fail_consequence", "return_to_camp_end_round"))
	assert_str(summary).contains(loss_label + "=" + _translate_token("key_loss_summary", "camp_hp_risk"))
	assert_str(summary).contains(round_label + "=6")
	assert_str(summary).not_contains(EVENT_TYPE)
	assert_str(summary).not_contains("win_rate_tier")
	assert_str(summary).not_contains("return_to_camp_end_round")
	assert_str(summary).not_contains("camp_hp_risk")

	_restore_locale(original_locale)

# ACC:T66.2
# Missing-locale fallback must stay observable and deterministic instead of collapsing to an empty summary.
func test_task66_a006_boss_challenge_prompt_fallback_summary_is_observable_when_locale_missing() -> void:
	var original_locale := _set_locale(LOCALE_MISSING)
	var hud := await _hud()

	_publish_boss_challenge_prompted(_boss_prompt_payload())
	var summary := await _await_event_summary(hud)
	var items := _event_log_messages(hud)
	var summary_label := _translate_field(EVENT_TYPE, "summary", "", "Boss challenge prompt")
	if summary_label == "Boss challenge prompt":
		summary_label = _try_translate("ui.hud.event.core.sanguo.boss.challenge.prompted.summary")
		if summary_label.length() == 0:
			summary_label = "Boss challenge prompt"
	var boss_label := _translate_field(EVENT_TYPE, "detail", "boss_id", "boss_id")
	var win_rate_label := _translate_field(EVENT_TYPE, "detail", "win_rate_tier", "win_rate_tier")
	var pressure_label := _translate_field(EVENT_TYPE, "detail", "next_round_pressure_forecast", "next_round_pressure_forecast")
	var fail_label := _translate_field(EVENT_TYPE, "detail", "fail_consequence", "fail_consequence")
	var loss_label := _translate_field(EVENT_TYPE, "detail", "key_loss_summary", "key_loss_summary")
	var round_label := _translate_field(EVENT_TYPE, "detail", "trigger_round", "round")

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(summary).is_not_empty()
	assert_int(items.size()).is_greater_equal(1)
	assert_str(str(items[items.size() - 1])).is_equal(summary)
	assert_str(summary).contains(summary_label)
	assert_str(summary).contains(boss_label + "=boss_1")
	assert_str(summary).contains(win_rate_label + "=" + _translate_token("win_rate_tier", "mid"))
	assert_str(summary).contains(pressure_label + "=4")
	assert_str(summary).contains(fail_label + "=" + _translate_token("fail_consequence", "return_to_camp_end_round"))
	assert_str(summary).contains(loss_label + "=" + _translate_token("key_loss_summary", "camp_hp_risk"))
	assert_str(summary).contains(round_label + "=6")
	assert_str(summary).not_contains("ui.hud.event.")

	_restore_locale(original_locale)

func test_task66_a006_boss_challenge_prompt_missing_fail_consequence_remains_non_empty() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud := await _hud()
	var payload := _boss_prompt_payload()
	payload.erase("FailConsequence")

	_publish_boss_challenge_prompted(payload)
	var summary := await _await_event_summary(hud)
	var summary_label := _require_translation("ui.hud.event.core.sanguo.boss.challenge.prompted.summary")
	var boss_label := _translate_field(EVENT_TYPE, "detail", "boss_id", "boss_id")
	var win_rate_label := _translate_field(EVENT_TYPE, "detail", "win_rate_tier", "win_rate_tier")
	var pressure_label := _translate_field(EVENT_TYPE, "detail", "next_round_pressure_forecast", "next_round_pressure_forecast")
	var loss_label := _translate_field(EVENT_TYPE, "detail", "key_loss_summary", "key_loss_summary")
	var round_label := _translate_field(EVENT_TYPE, "detail", "trigger_round", "round")
	var fail_label := _translate_field(EVENT_TYPE, "detail", "fail_consequence", "fail_consequence")

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(summary).is_not_empty()
	assert_str(summary).contains(summary_label)
	assert_str(summary).contains(boss_label + "=boss_1")
	assert_str(summary).contains(win_rate_label + "=" + _translate_token("win_rate_tier", "mid"))
	assert_str(summary).contains(pressure_label + "=4")
	assert_str(summary).contains(loss_label + "=" + _translate_token("key_loss_summary", "camp_hp_risk"))
	assert_str(summary).contains(round_label + "=6")
	assert_str(summary).not_contains(fail_label + "=")

	_restore_locale(original_locale)
