extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CONTROLLER_PATH := "res://Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs"
const REJECTION_EVENT := "ui.sanguo.advance_turn.rejected"
const GAME_ENDED_EVENT := "core.sanguo.game.ended"
const TURN_ADVANCED_EVENT := "core.sanguo.game.turn.advanced"
const TURN_STARTED_EVENT := "core.sanguo.game.turn.started"
const PLAYER_ELIMINATED_EVENT := "core.sanguo.player.eliminated"

var _bus: Node
var _events: Array = []

func before() -> void:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
	_events = []

func _on_domain_event_emitted(type, source, data_json, id, spec_version, data_content_type, timestamp_iso) -> void:
	_events.append({
		"type": str(type),
		"source": str(source),
		"data_json": str(data_json),
		"id": str(id),
		"spec_version": str(spec_version),
		"data_content_type": str(data_content_type),
		"timestamp_iso": str(timestamp_iso),
	})

func _read_res_text(path: String) -> String:
	var file := FileAccess.open(path, FileAccess.READ)
	assert_object(file).is_not_null()
	return file.get_as_text()

func _events_of_type(type_name: String) -> Array:
	var result: Array = []
	for event in _events:
		if str(event.get("type", "")) == type_name:
			result.append(event)
	return result

func _payload(event: Dictionary) -> Dictionary:
	var parsed = JSON.parse_string(str(event.get("data_json", "{}")))
	if parsed is Dictionary:
		return parsed
	return {}

func _publish(type_name: String, payload: Dictionary) -> void:
	_bus.PublishSimple(type_name, "ut", JSON.stringify(payload))

func _assert_no_turn_progress_after(event_count_before: int) -> void:
	for index in range(event_count_before, _events.size()):
		var event_type := str((_events[index] as Dictionary).get("type", ""))
		assert_str(event_type).is_not_equal(TURN_ADVANCED_EVENT)
		assert_str(event_type).is_not_equal(TURN_STARTED_EVENT)

# acceptance: ACC:T197.10
func test_gameover_advanceturn_rejection_is_adapter_visible_and_does_not_publish_turn_progress() -> void:
	var source := _read_res_text(CONTROLLER_PATH)
	assert_str(source).contains(REJECTION_EVENT)
	assert_str(source).contains("PublishAdvanceTurnRejected(correlationId, UiHudDiceRoll, ex)")
	assert_str(source).contains("PublishAdvanceTurnRejected(correlationId, UiActionCardPlay, ex)")
	assert_str(source).contains("PublishAdvanceTurnRejected(correlationId, UiTileActionSelected, ex)")
	assert_str(source).contains("PublishAdvanceTurnRejected(correlationId, AiAutoAdvanceCausationId, ex)")
	assert_str(source).contains("_bus.PublishSimple(UiAdvanceTurnRejected")
	assert_str(source).contains("InvalidOperationException")
	assert_str(source).contains("GameOver")

	var before_invalid_advance := _events.size()
	_publish(REJECTION_EVENT, {
		"CorrelationId": "corr-after-gameover",
		"CausationId": "ui.hud.dice.roll",
		"Reason": "GameOver: EndReason=player_bankrupt"
	})
	await get_tree().process_frame

	_assert_no_turn_progress_after(before_invalid_advance)
	var rejected := _events_of_type(REJECTION_EVENT)
	assert_int(rejected.size()).is_equal(1)
	var rejected_payload := _payload(rejected[0])
	assert_str(str(rejected_payload.get("Reason", ""))).contains("GameOver")
	assert_str(str(rejected_payload.get("CorrelationId", ""))).is_equal("corr-after-gameover")

# acceptance: ACC:T197.11
func test_npc_bankruptcy_rotation_is_adapter_visible_without_reselecting_eliminated_npc() -> void:
	var source := _read_res_text(CONTROLLER_PATH)
	assert_str(source).contains("ActivePlayerId")

	_publish(PLAYER_ELIMINATED_EVENT, {
		"GameId": "g1",
		"TurnNumber": 3,
		"PlayerId": "ai-1",
		"ReasonCode": "bankrupt",
		"MoneyBefore": 5,
		"MoneyAfter": 0
	})
	_publish(TURN_ADVANCED_EVENT, {
		"GameId": "g1",
		"TurnNumber": 4,
		"ActivePlayerId": "p2",
		"CorrelationId": "corr-after-npc-bankruptcy"
	})
	_publish(TURN_STARTED_EVENT, {
		"GameId": "g1",
		"TurnNumber": 4,
		"ActivePlayerId": "p2",
		"CorrelationId": "corr-after-npc-bankruptcy"
	})

	var eliminated_npcs := {}
	for event in _events_of_type(PLAYER_ELIMINATED_EVENT):
		var eliminated_payload := _payload(event)
		if str(eliminated_payload.get("ReasonCode", "")) == "bankrupt":
			eliminated_npcs[str(eliminated_payload.get("PlayerId", ""))] = true

	assert_bool(eliminated_npcs.has("ai-1")).is_true()
	for event in _events:
		var event_type := str((event as Dictionary).get("type", ""))
		if event_type != TURN_ADVANCED_EVENT and event_type != TURN_STARTED_EVENT:
			continue
		var turn_payload := _payload(event)
		assert_bool(eliminated_npcs.has(str(turn_payload.get("ActivePlayerId", "")))).is_false()
