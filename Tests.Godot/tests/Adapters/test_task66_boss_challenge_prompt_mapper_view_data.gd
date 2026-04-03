extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE := "core.sanguo.boss.challenge.prompted"
const LOCALE_ZH := "zh"

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

func _event_log_messages(hud: Node) -> Array:
	var panel: Control = hud.get_node("EventLogPanel")
	var list: ItemList = panel.get_node("Margin/VBox/EventList")
	var items: Array = []
	for index in range(list.item_count):
		items.append(str(list.get_item_text(index)))
	return items

func _await_event_log_items(hud: Node, min_count: int, max_frames: int = 20) -> Array:
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

func _read_utf8_text(path: String) -> String:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return ""
	return file.get_as_text()

# ACC:T66.3
# Transport-only fields must not change the UI-facing summary emitted by the current summary-only handler chain.
func test_task66_boss_challenge_prompt_summary_is_transport_independent() -> void:
	var original_locale := _set_locale(LOCALE_ZH)
	var hud := await _hud()
	var payload_a := _boss_prompt_payload()
	var payload_b := _boss_prompt_payload()
	payload_b["CorrelationId"] = "corr-1"
	payload_b["CausationId"] = "cause-1"
	payload_b["TransportEnvelope"] = {"source": "ut", "type": EVENT_TYPE}

	_publish_boss_challenge_prompted(payload_a)
	var items_a := await _await_event_log_items(hud, 1)
	var summary_a := str(items_a[items_a.size() - 1])

	_publish_boss_challenge_prompted(payload_b)
	var items_b := await _await_event_log_items(hud, 2)
	var summary_b := str(items_b[items_b.size() - 1])

	var boss_label := _translate_field(EVENT_TYPE, "detail", "boss_id", "boss_id")
	var win_rate_label := _translate_field(EVENT_TYPE, "detail", "win_rate_tier", "win_rate_tier")
	var pressure_label := _translate_field(EVENT_TYPE, "detail", "next_round_pressure_forecast", "next_round_pressure_forecast")
	var loss_label := _translate_field(EVENT_TYPE, "detail", "key_loss_summary", "key_loss_summary")
	var fail_label := _translate_field(EVENT_TYPE, "detail", "fail_consequence", "fail_consequence")
	var round_label := _translate_field(EVENT_TYPE, "detail", "trigger_round", "round")

	assert_str(summary_a).is_not_empty()
	assert_str(summary_b).is_equal(summary_a)
	assert_str(summary_b).contains(boss_label + "=boss_1")
	assert_str(summary_b).contains(win_rate_label + "=" + _translate_token("win_rate_tier", "mid"))
	assert_str(summary_b).contains(pressure_label + "=4")
	assert_str(summary_b).contains(loss_label + "=" + _translate_token("key_loss_summary", "camp_hp_risk"))
	assert_str(summary_b).contains(fail_label + "=" + _translate_token("fail_consequence", "return_to_camp_end_round"))
	assert_str(summary_b).contains(round_label + "=6")
	assert_str(summary_b).not_contains("CorrelationId")
	assert_str(summary_b).not_contains("TransportEnvelope")
	assert_str(summary_b).not_contains(EVENT_TYPE)

	_restore_locale(original_locale)

# Auxiliary guard: keep a lightweight source-level check around the current
# summary-only registry wiring until a later task introduces a dedicated prompt flow.
func test_task66_boss_challenge_prompt_runtime_path_remains_deferred() -> void:
	var explain_source := _read_utf8_text("res://Game.Godot/Scripts/UI/EventExplainService.cs")
	var registry_source := _read_utf8_text("res://Game.Godot/Scripts/UI/HudEventHandlerRegistry.cs")

	assert_str(explain_source).is_not_empty()
	assert_str(registry_source).is_not_empty()
	assert_str(explain_source).contains("SanguoBossChallengePrompted.EventType")
	assert_str(registry_source).contains("controller.Register(SanguoBossChallengePrompted.EventType, _ => handlers.HandleUiOnly());")
	assert_str(registry_source).not_contains("HandleBossChallengePrompt")
