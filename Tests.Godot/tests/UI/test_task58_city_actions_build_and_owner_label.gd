extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_TYPE_TOKEN_MOVED := "core.sanguo.board.token.moved"
const EVENT_TYPE_UI_ACTION_SELECTED := "ui.sanguo.tile.action.selected"

var _bus: Node
var _emitted_types: Array[String] = []
var _last_ui_action_payload: Dictionary = {}

func before() -> void:
	_emitted_types = []
	_last_ui_action_payload = {}

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	var t := str(type)
	if _emitted_types.size() < 64:
		_emitted_types.append(t)

	if t != EVENT_TYPE_UI_ACTION_SELECTED:
		return

	var parsed: Variant = JSON.parse_string(str(data_json))
	if typeof(parsed) == TYPE_DICTIONARY:
		_last_ui_action_payload = parsed as Dictionary

func _hud() -> Node:
	var hud := preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _action_label_candidates(action_id: String) -> Array[String]:
	var normalized := action_id.strip_edges().to_lower()
	var candidates: Array[String] = []
	if normalized.length() == 0:
		return candidates

	candidates.append(normalized)
	if TranslationServer.has_method("translate"):
		var key := "ui.hud.action.%s" % normalized
		var translated := String(TranslationServer.translate(key)).strip_edges()
		if translated.length() > 0 and translated != key and not candidates.has(translated):
			candidates.append(translated)
	return candidates

func _find_action_button(actions_box: Node, action_id: String) -> Button:
	var candidates := _action_label_candidates(action_id)
	for child in actions_box.get_children():
		if not (child is Button):
			continue
		var button_text := str((child as Button).text).strip_edges()
		for candidate in candidates:
			if button_text.to_lower() == str(candidate).to_lower():
				return child as Button
	return null

# ACC:T58.3
# ACC:T58.4
func test_task58_city_actions_build_and_skip_are_executable() -> void:
	var hud := await _hud()
	var action_panel: Control = hud.get_node("ActionPanel")
	var actions_box: VBoxContainer = hud.get_node("ActionPanel/VBox/Actions")
	var skip_btn: Button = hud.get_node("ActionPanel/VBox/SkipButton")
	assert_object(skip_btn).is_not_null()
	if skip_btn == null:
		return

	# Enable human tile action panel: active player must be set.
	_bus.PublishSimple(EVENT_TYPE_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":3,\"Month\":2,\"Day\":1}")
	await get_tree().process_frame

	# Trigger action panel by simulating a move to a tile with actions (map index 0 has buy_land/build in Data/maps/map001.json).
	_bus.PublishSimple(EVENT_TYPE_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":0,\"Steps\":0,\"PassedStart\":false,\"CorrelationId\":\"corr-1\"}")
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_true()

	# Build must NOT be shown for unowned cities.
	var build_btn_unowned := _find_action_button(actions_box, "build")
	assert_object(build_btn_unowned).is_null()

	# Make the landing city owned, so the build action becomes available.
	_bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"TurnNumber\":1,\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":0,\"OccurredAt\":\"2026-01-01T00:00:00Z\",\"CorrelationId\":\"corr\",\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":2}}")
	await get_tree().process_frame

	_bus.PublishSimple(EVENT_TYPE_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":0,\"Steps\":0,\"PassedStart\":false,\"CorrelationId\":\"corr-2\"}")
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_true()

	var build_btn := _find_action_button(actions_box, "build")
	assert_object(build_btn).is_not_null()
	if build_btn == null:
		return

	build_btn.pressed.emit()
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_false()
	assert_str(str(_last_ui_action_payload.get("Action", ""))).is_equal("build")

	# Show again and validate Skip publishes and closes.
	_bus.PublishSimple(EVENT_TYPE_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":0,\"Steps\":0,\"PassedStart\":false,\"CorrelationId\":\"corr-3\"}")
	await get_tree().process_frame
	assert_bool(action_panel.visible).is_true()

	skip_btn.pressed.emit()
	await get_tree().process_frame

	assert_bool(action_panel.visible).is_false()
	assert_str(str(_last_ui_action_payload.get("Action", ""))).is_equal("skip")
