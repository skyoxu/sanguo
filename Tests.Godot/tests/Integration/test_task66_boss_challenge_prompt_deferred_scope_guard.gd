extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# Task 66 integration tests (red-first).
# ADR refs:
# - ADR-0004 (event contracts / type discipline)
# - ADR-0005 (quality gates)

const EVENT_TYPE_BOSS_CHALLENGE_PROMPTED := "core.sanguo.boss.challenge.prompted"

var _bus: Node

func before() -> void:
	get_tree().paused = false

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func after() -> void:
	get_tree().paused = false

func _hud() -> Node:
	var hud := preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _publish_boss_challenge_prompted() -> void:
	var payload := JSON.stringify({
		"GameId": "g1",
		"BossId": "boss_1",
		"RoundNumber": 6,
		"WinRateTier": "mid",
		"NextRoundPressureForecast": 4,
		"KeyLossSummary": "camp_hp_risk",
		"FailConsequence": "return_to_camp_end_round",
	})
	_bus.PublishSimple(EVENT_TYPE_BOSS_CHALLENGE_PROMPTED, "ut", payload)

func _toast_visible(hud: Node) -> bool:
	var toast: Control = hud.get_node("EventToast")
	return bool(toast.visible)

func _toast_label_text(hud: Node) -> String:
	var toast: Control = hud.get_node("EventToast")
	var label: Label = toast.get_node("Panel/Label")
	return str(label.text)

func _result_popup_visible(hud: Node) -> bool:
	var popup: Control = hud.get_node("EventResultPopup")
	return bool(popup.visible)

func _card_confirm_visible(hud: Node) -> bool:
	var confirm: Control = hud.get_node("CardsPanel/CardConfirm")
	return bool(confirm.visible)

func _read_utf8_text(path: String) -> String:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return ""
	return file.get_as_text()

# ACC:T66.5
# Deferred-scope guard: the publish frame may render summary-only UI,
# but it must not open a blocking prompt or confirm surface inside the current runtime path.
func test_task66_boss_challenge_prompt_remains_summary_only_on_publish_frame() -> void:
	var hud := await _hud()

	assert_bool(_toast_visible(hud)).is_false()
	assert_bool(_result_popup_visible(hud)).is_false()
	assert_bool(_card_confirm_visible(hud)).is_false()
	assert_bool(get_tree().paused).is_false()

	_publish_boss_challenge_prompted()

	assert_bool(_toast_visible(hud)).is_true()
	assert_str(_toast_label_text(hud)).is_not_empty()
	assert_bool(_result_popup_visible(hud)).is_false()
	assert_bool(_card_confirm_visible(hud)).is_false()
	assert_bool(get_tree().paused).is_false()

# The current runtime remains summary-only; a future prompt flow must not be implied by hidden handler wiring.
func test_task66_boss_challenge_prompt_future_runtime_boundary_is_not_implemented_yet() -> void:
	var registry_source := _read_utf8_text("res://Game.Godot/Scripts/UI/HudEventHandlerRegistry.cs")
	var handlers_source := _read_utf8_text("res://Game.Godot/Scripts/UI/IHudEventHandlers.cs")
	var hud_source := _read_utf8_text("res://Game.Godot/Scripts/UI/HUD.cs")

	assert_str(registry_source).is_not_empty()
	assert_str(handlers_source).is_not_empty()
	assert_str(hud_source).is_not_empty()

	var has_explicit_deferred_boundary := (
		hud_source.contains("CallDeferred(nameof(ShowBossChallengePrompt")
		or hud_source.contains("CallDeferred(nameof(HandleBossChallengePrompt")
		or hud_source.contains("CallDeferred(\"ShowBossChallengePrompt\")")
		or hud_source.contains("CallDeferred(\"HandleBossChallengePrompt\")")
	)
	var still_ui_only := registry_source.contains("controller.Register(SanguoBossChallengePrompted.EventType, _ => handlers.HandleUiOnly());")
	var has_no_dedicated_handler_contract := not handlers_source.contains("HandleBossChallengePrompt")

	assert_bool(still_ui_only).is_true()
	assert_bool(has_no_dedicated_handler_contract).is_true()
	assert_bool(has_explicit_deferred_boundary).is_false()
