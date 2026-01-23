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

func _publish_random_event_applied(picked_id: String, message: String) -> void:
	var json := "{\"PickedId\":\"%s\",\"PickedIndex\":0,\"RngContextId\":\"ut:turn:1:round:1:src\",\"CandidatesSortedIdsHash\":\"deadbeef\",\"AppliedMultipliersAfter\":{\"Event\":{\"Steps\":1}},\"UiMessage\":\"%s\"}" % [picked_id, message]
	_bus.PublishSimple(EVENT_TYPE_RANDOM_EVENT_APPLIED, "ut", json)


# ACC:T56.3
# After a random event is applied, the UI must show a visible prompt, and the prompt content must be derived from the payload.
func test_task56_hud_event_prompt_is_visible_and_uses_payload_text() -> void:
	var hud := await _hud()

	_publish_random_event_applied("ev_lucky_gold", "A lucky find increases your funds.")
	for _i in range(60):
		if _toast_visible(hud) and _toast_label_text(hud).strip_edges() != "":
			break
		await get_tree().process_frame

	assert_bool(_toast_visible(hud)).is_true()
	var text := _toast_label_text(hud)
	assert_str(text).is_not_empty()
	assert_str(text).contains("ev_lucky_gold")


# ACC:T56.4
# Prompt content must change when payload changes (guards against hardcoded/unrelated content).
func test_task56_hud_event_prompt_updates_when_payload_changes() -> void:
	var hud := await _hud()

	_publish_random_event_applied("ev_a", "Payload A")
	for _i in range(60):
		if _toast_visible(hud) and _toast_label_text(hud).strip_edges() != "":
			break
		await get_tree().process_frame
	var text_a := _toast_label_text(hud)

	_publish_random_event_applied("ev_b", "Payload B")
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
