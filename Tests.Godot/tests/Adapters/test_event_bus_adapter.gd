extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE := "core.sanguo.task190.event"

class _EventCapture:
	extends RefCounted
	var types: Array[String] = []
	var payloads: Array[String] = []

	func on_emitted(type: String, _source: String, data_json: String, _id: String, _spec: String, _ct: String, _ts: String) -> void:
		types.append(type)
		payloads.append(data_json)

class _EconomyProjection:
	extends RefCounted
	var active_multiplier := 0.0
	var applied_amount := 0

	func on_emitted(type: String, _source: String, data_json: String, _id: String, _spec: String, _ct: String, _ts: String) -> void:
		if type != "core.sanguo.economy.month.settled":
			return

		var parsed = JSON.parse_string(data_json)
		if typeof(parsed) != TYPE_DICTIONARY:
			return

		var applied: Dictionary = parsed.get("AppliedMultipliers", {})
		active_multiplier = float(applied.get("EffectiveMultiplier", 0.0))
		applied_amount = int(parsed.get("AppliedAmount", 0))

class _SettlementProjection:
	extends RefCounted
	var finalized := false
	var winner := ""
	var final_balance := 0
	var observed_turns_after_final := 0

	func on_emitted(type: String, _source: String, data_json: String, _id: String, _spec: String, _ct: String, _ts: String) -> void:
		var parsed = JSON.parse_string(data_json)
		if typeof(parsed) != TYPE_DICTIONARY:
			parsed = {}

		if type == "core.sanguo.game.ended":
			if finalized:
				return
			finalized = true
			winner = str(parsed.get("WinnerPlayerId", ""))
			final_balance = int(parsed.get("FinalBalance", 0))
			return

		if type == "core.sanguo.game.turn.started" and finalized:
			observed_turns_after_final += 1
			return

func _new_bus(name: String = "Task190EventBus") -> Node:
	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = name
	add_child(auto_free(bus))
	return bus

# ACC:T190.6
func test_event_bus_publishsimple_preserves_order_for_same_inputs() -> void:
	var bus := _new_bus()
	var capture := _EventCapture.new()
	var handler := Callable(capture, "on_emitted")

	bus.DomainEventEmitted.connect(handler)
	bus.call("PublishSimple", EVENT_TYPE + ".1", "ut", "{\"seq\":1}")
	bus.call("PublishSimple", EVENT_TYPE + ".2", "ut", "{\"seq\":2}")
	await get_tree().process_frame
	bus.DomainEventEmitted.disconnect(handler)

	assert_int(capture.types.size()).is_equal(2)
	assert_str(capture.types[0]).is_equal(EVENT_TYPE + ".1")
	assert_str(capture.types[1]).is_equal(EVENT_TYPE + ".2")
	assert_str(capture.payloads[0]).contains("\"seq\":1")
	assert_str(capture.payloads[1]).contains("\"seq\":2")

# ACC:T190.5
func test_event_bus_economy_projection_exposes_applied_multiplier_effect() -> void:
	var bus := _new_bus()
	var projection := _EconomyProjection.new()
	var handler := Callable(projection, "on_emitted")

	bus.DomainEventEmitted.connect(handler)
	bus.call("PublishSimple", "core.sanguo.economy.month.settled", "ut", "{\"BaseAmount\":100,\"AppliedAmount\":150,\"AppliedMultipliers\":{\"CharacterStepDelta\":0,\"BuildingStepDelta\":1,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"EffectiveMultiplier\":1.5}}")
	await get_tree().process_frame
	bus.DomainEventEmitted.disconnect(handler)

	assert_float(projection.active_multiplier).is_equal(1.5)
	assert_int(projection.applied_amount).is_equal(150)

# ACC:T190.7
# ACC:T190.9
func test_event_bus_game_end_event_remains_stable_under_follow_up_events() -> void:
	var bus := _new_bus()
	var capture := _EventCapture.new()
	var projection := _SettlementProjection.new()
	var handler := Callable(capture, "on_emitted")
	var projection_handler := Callable(projection, "on_emitted")

	bus.DomainEventEmitted.connect(handler)
	bus.DomainEventEmitted.connect(projection_handler)
	var game_end_payload := "{\"WinnerPlayerId\":\"p1\",\"EndReason\":\"max_turns\",\"Settled\":true,\"FinalBalance\":240}"
	bus.call("PublishSimple", "core.sanguo.game.ended", "ut", game_end_payload)
	bus.call("PublishSimple", "core.sanguo.game.turn.started", "ut", "{\"ActivePlayerId\":\"p2\",\"FinalBalance\":999}")
	bus.call("PublishSimple", "core.sanguo.game.ended", "ut", "{\"WinnerPlayerId\":\"p2\",\"EndReason\":\"late_mutation\",\"Settled\":true,\"FinalBalance\":999}")
	await get_tree().process_frame
	bus.DomainEventEmitted.disconnect(projection_handler)
	bus.DomainEventEmitted.disconnect(handler)

	assert_int(capture.types.size()).is_equal(3)
	assert_str(capture.types[0]).is_equal("core.sanguo.game.ended")
	assert_str(capture.payloads[0]).is_equal(game_end_payload)
	assert_str(capture.types[1]).is_equal("core.sanguo.game.turn.started")
	assert_bool(projection.finalized).is_true()
	assert_str(projection.winner).is_equal("p1")
	assert_int(projection.final_balance).is_equal(240)
	assert_int(projection.observed_turns_after_final).is_equal(1)
