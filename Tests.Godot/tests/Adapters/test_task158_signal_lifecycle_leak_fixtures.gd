extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TURN_ENDED := "core.sanguo.game.turn.ended"

class IntHolder:
	extends RefCounted
	var value: int

	func _init(v: int = 0) -> void:
		value = v

class LeakFixtureState:
	var leaked_handler_retained: bool
	var invocation_after_dispose: int

	func _init(leaked: bool, invocations: int) -> void:
		leaked_handler_retained = leaked
		invocation_after_dispose = invocations

func _new_bus() -> Node:
	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "Task158LeakFixtureBus"
	add_child(auto_free(bus))
	return bus

func _create_leak_fixture(bus: Node) -> LeakFixtureState:
	var retained := IntHolder.new(0)
	var handler := func(type: String, _source: String, _json: String, _id: String, _spec: String, _data_content_type: String, _ts: String) -> void:
		if type == EVENT_TURN_ENDED:
			retained.value += 1

	bus.DomainEventEmitted.connect(handler)
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":1}")
	# Leak fixture intentionally omits disconnect; second publish should still trigger handler.
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":2}")
	bus.DomainEventEmitted.disconnect(handler)
	return LeakFixtureState.new(true, retained.value)


func _create_clean_fixture(bus: Node) -> LeakFixtureState:
	var retained := IntHolder.new(0)
	var handler := func(type: String, _source: String, _json: String, _id: String, _spec: String, _data_content_type: String, _ts: String) -> void:
		if type == EVENT_TURN_ENDED:
			retained.value += 1

	bus.DomainEventEmitted.connect(handler)
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":1}")
	bus.DomainEventEmitted.disconnect(handler)
	var after_disconnect := retained.value
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":2}")
	return LeakFixtureState.new(false, retained.value - after_disconnect)


# ACC:T158.1
func test_should_expose_task165_leak_fixture_signal_for_master_closure_evidence() -> void:
	var bus := _new_bus()
	var leak_state := _create_leak_fixture(bus)
	var clean_state := _create_clean_fixture(bus)

	assert_bool(leak_state.leaked_handler_retained).is_true()
	assert_int(leak_state.invocation_after_dispose).is_equal(2)
	assert_bool(clean_state.leaked_handler_retained).is_false()
	assert_int(clean_state.invocation_after_dispose).is_equal(0)
