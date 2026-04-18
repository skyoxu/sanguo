extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
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
	bus.name = "Task158SignalLifecycleBus"
	add_child(auto_free(bus))
	return bus


func _publish_turn_events(bus: Node) -> void:
	bus.PublishSimple(EVENT_TURN_STARTED, "gdunit", "{\"Turn\":1}")
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":1}")


func _create_leak_fixture(bus: Node) -> LeakFixtureState:
	var retained := IntHolder.new(0)
	var handler := func(type: String, _source: String, _json: String, _id: String, _spec: String, _data_content_type: String, _ts: String) -> void:
		if type == EVENT_TURN_ENDED:
			retained.value += 1

	bus.DomainEventEmitted.connect(handler)
	_publish_turn_events(bus)
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
	_publish_turn_events(bus)
	bus.DomainEventEmitted.disconnect(handler)
	var after_disconnect := retained.value
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":2}")
	return LeakFixtureState.new(false, retained.value - after_disconnect)


# ACC:T164.1
func test_should_require_matching_subscribe_unsubscribe_without_remaining_listener_for_turn_events() -> void:
	var bus := _new_bus()
	var active := 0
	var peak := 0
	var handled_started := IntHolder.new(0)
	var handled_ended := IntHolder.new(0)
	var handler := func(type: String, _source: String, _json: String, _id: String, _spec: String, _data_content_type: String, _ts: String) -> void:
		if type == EVENT_TURN_STARTED:
			handled_started.value += 1
		if type == EVENT_TURN_ENDED:
			handled_ended.value += 1

	active += 1
	peak = maxi(peak, active)
	bus.DomainEventEmitted.connect(handler)

	_publish_turn_events(bus)
	bus.DomainEventEmitted.disconnect(handler)
	active -= 1
	var started_after_unsubscribe := handled_started.value
	var ended_after_unsubscribe := handled_ended.value
	_publish_turn_events(bus)

	assert_int(peak).is_equal(1)
	assert_int(active).is_equal(0)
	assert_int(started_after_unsubscribe).is_equal(1)
	assert_int(ended_after_unsubscribe).is_equal(1)
	assert_int(handled_started.value).is_equal(started_after_unsubscribe)
	assert_int(handled_ended.value).is_equal(ended_after_unsubscribe)


# ACC:T165.1
func test_should_detect_stale_handler_leak_fixture_and_keep_clean_fixture_without_stale_invocation() -> void:
	var bus := _new_bus()
	var leak_state := _create_leak_fixture(bus)
	var clean_state := _create_clean_fixture(bus)

	assert_bool(leak_state.leaked_handler_retained).is_true()
	assert_int(leak_state.invocation_after_dispose).is_equal(2)
	assert_bool(clean_state.leaked_handler_retained).is_false()
	assert_int(clean_state.invocation_after_dispose).is_equal(0)
