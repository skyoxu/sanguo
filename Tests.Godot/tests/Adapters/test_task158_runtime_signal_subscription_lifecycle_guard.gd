extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_TURN_ENDED := "core.sanguo.game.turn.ended"

class IntHolder:
	extends RefCounted
	var value: int

	func _init(v: int = 0) -> void:
		value = v

# Use the real adapter path as split-task evidence anchor (T164), not local mock classes.
func _new_bus() -> Node:
	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "Task158RuntimeSubscriptionBus"
	add_child(auto_free(bus))
	return bus

# ACC:T158.1
func test_should_track_runtime_subscription_guard_for_task164_closure_evidence() -> void:
	var bus := _new_bus()
	var active := 0
	var peak := 0
	var started_count := IntHolder.new(0)
	var ended_count := IntHolder.new(0)
	var handler := func(type: String, _source: String, _json: String, _id: String, _spec: String, _data_content_type: String, _ts: String) -> void:
		if type == EVENT_TURN_STARTED:
			started_count.value += 1
		if type == EVENT_TURN_ENDED:
			ended_count.value += 1

	active += 1
	peak = maxi(peak, active)
	bus.DomainEventEmitted.connect(handler)

	bus.PublishSimple(EVENT_TURN_STARTED, "gdunit", "{\"Turn\":1}")
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":1}")
	bus.DomainEventEmitted.disconnect(handler)
	active -= 1
	var started_after_unsubscribe := started_count.value
	var ended_after_unsubscribe := ended_count.value

	# Verify unsubscribe by publishing again after disconnect.
	bus.PublishSimple(EVENT_TURN_STARTED, "gdunit", "{\"Turn\":2}")
	bus.PublishSimple(EVENT_TURN_ENDED, "gdunit", "{\"Turn\":2}")

	assert_int(peak).is_equal(1)
	assert_int(active).is_equal(0)
	assert_int(started_after_unsubscribe).is_equal(1)
	assert_int(ended_after_unsubscribe).is_equal(1)
	assert_int(started_count.value).is_equal(started_after_unsubscribe)
	assert_int(ended_count.value).is_equal(ended_after_unsubscribe)
