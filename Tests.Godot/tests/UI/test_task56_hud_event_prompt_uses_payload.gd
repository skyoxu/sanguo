extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Task 56 UI acceptance tests (red-first).
# ADR refs:
# - ADR-0004 (event contracts / CloudEvents type discipline)
# - ADR-0005 (quality gates)
# Contract context: core.sanguo.random_event.applied (SanguoRandomEventApplied).

const EVENT_TYPE_RANDOM_EVENT_APPLIED := "core.sanguo.random_event.applied"

var _bus: Node

func before() -> void:
	# Install a temporary EventBus under /root to mimic Autoload.
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _toast_label_text(hud: Node) -> String:
	var toast: Control = hud.get_node("EventToast")
	var label: Label = toast.get_node("Panel/Label")
	return str(label.text)

func _toast_visible(hud: Node) -> bool:
	var toast: Control = hud.get_node("EventToast")
	return bool(toast.visible)

func _try_translate(key: String) -> String:
	if TranslationServer.has_method("translate"):
		var t := String(TranslationServer.translate(key))
		if t.strip_edges().length() > 0 and t != key:
			return t
	return ""

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

func _publish_random_event_applied(picked_id: String, event_id: String, message: String, rng_context: String, effect_kind: String, money_delta: int, step_delta: int, trigger_source: String = "") -> void:
	var json = "{\"EventId\":\"%s\",\"PickedId\":\"%s\",\"EffectKind\":\"%s\",\"MoneyDelta\":%d,\"StepDelta\":%d,\"RngContextId\":\"%s\",\"CandidatesSortedIdsHash\":\"deadbeef\",\"UiMessage\":\"%s\"}" % [event_id, picked_id, effect_kind, money_delta, step_delta, rng_context, message]
	if trigger_source.strip_edges().length() > 0:
		json = json.substr(0, json.length() - 1) + ",\"TriggerSource\":\"%s\"}" % trigger_source
	_bus.PublishSimple(EVENT_TYPE_RANDOM_EVENT_APPLIED, "ut", json)


# ACC:T56.3
# After a random event is applied, the UI must show a visible prompt, and the prompt content must be derived from the payload.
func test_task56_hud_event_prompt_is_visible_and_uses_payload_text() -> void:
	var hud := await _hud()

	_publish_random_event_applied(
		"ev_lucky_gold",
		"ev_lucky_gold",
		"A lucky find increases your funds.",
		"rng.random_events:1:2:tile",
		"moneyDelta",
		5,
		1
	)
	for _i in range(60):
		if _toast_visible(hud) and _toast_label_text(hud).strip_edges() != "":
			break
		await get_tree().process_frame

	assert_bool(_toast_visible(hud)).is_true()
	var text := _toast_label_text(hud)
	assert_str(text).is_not_empty()
	assert_str(text).contains("ev_lucky_gold")
	var source_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source", "source")
	var source_tile := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source.tile", "tile")
	var round_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_round", "round")
	var money_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "delta", "money_delta", "money_delta")
	var next_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "next_step", "next_step")
	var next_continue := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "next_step.continue", "continue")
	assert_str(text).contains(source_label + "=" + source_tile)
	assert_str(text).contains(round_label + "=2")
	assert_str(text).contains(money_label + "=+5")
	assert_str(text).contains(next_label + "=" + next_continue)


# ACC:T56.4
# Prompt content must change when payload changes (guards against hardcoded/unrelated content).
func test_task56_hud_event_prompt_updates_when_payload_changes() -> void:
	var hud := await _hud()

	_publish_random_event_applied(
		"ev_a",
		"ev_a",
		"Payload A",
		"rng.random_events:1:1:tile",
		"moneyDelta",
		1,
		0
	)
	for _i in range(60):
		if _toast_visible(hud) and _toast_label_text(hud).strip_edges() != "":
			break
		await get_tree().process_frame
	var text_a := _toast_label_text(hud)

	_publish_random_event_applied(
		"ev_b",
		"global:ev_b",
		"Payload B",
		"rng.random_events:5:3:global",
		"moneyDelta",
		2,
		0
	)
	for _j in range(60):
		var t := _toast_label_text(hud)
		if _toast_visible(hud) and t.strip_edges() != "" and t != text_a:
			break
		await get_tree().process_frame
	var text_b := _toast_label_text(hud)

	assert_str(text_a).is_not_empty()
	assert_str(text_b).is_not_empty()
	assert_str(text_a).contains("ev_a")
	assert_str(text_b).contains("ev_b")
	assert_bool(text_a != text_b).is_true()
	var source_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source", "source")
	var source_global := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source.global", "global")
	var next_label := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "next_step", "next_step")
	var next_continue := _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "next_step.continue", "continue")
	assert_str(text_b).contains(source_label + "=" + source_global)
	assert_str(text_b).contains(next_label + "=" + next_continue)


# ACC:T56.5
# TriggerSource must be honored when present, even if RNG context implies a different source.
func test_task56_hud_event_prompt_prefers_explicit_trigger_source() -> void:
	var hud = await _hud()

	_publish_random_event_applied(
		"ev_tile",
		"ev_tile",
		"Payload C",
		"rng.random_events:2:2:tile",
		"moneyDelta",
		3,
		0,
		"global"
	)
	for _i in range(60):
		if _toast_visible(hud) and _toast_label_text(hud).strip_edges() != "":
			break
		await get_tree().process_frame

	var text = _toast_label_text(hud)
	var source_label = _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source", "source")
	var source_global = _translate_field(EVENT_TYPE_RANDOM_EVENT_APPLIED, "detail", "trigger_source.global", "global")
	assert_str(text).contains(source_label + "=" + source_global)
