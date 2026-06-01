extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_CITY_BOUGHT := "core.sanguo.city.bought"

var _bus: Node

func before() -> void:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _main() -> Node:
	var main := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	return main

# ACC:T58.3
# ACC:T189.12
# ACC:T189.13
func test_task58_city_owner_label_updates_on_city_bought() -> void:
	var main := await _main()

	var label: Label = main.get_node("SplitRoot/BottomArea/BoardArea/Overlays/CityOwnershipStatus/OwnershipStatusLabel")
	assert_bool(label.text.contains("Unowned") or label.text.contains("无主")).is_true()

	_bus.PublishSimple(EVENT_TYPE_CITY_BOUGHT, "ut", "{\"GameId\":\"g1\",\"TurnNumber\":1,\"BuyerId\":\"p1\",\"CityId\":\"c1\",\"Price\":0,\"OccurredAt\":\"2026-01-01T00:00:00Z\",\"CorrelationId\":\"corr\",\"AppliedMultipliers\":{\"BaseSteps\":2,\"CharacterStepDelta\":0,\"BuildingStepDelta\":0,\"EventStepDelta\":0,\"ActionCardStepDelta\":0,\"RelicStepDelta\":0,\"RegionStepDelta\":0,\"EffectiveSteps\":2}}")
	await get_tree().process_frame

	assert_bool(label.text.contains("p1")).is_true()
