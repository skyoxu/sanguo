extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TURN_ADVANCED := "core.sanguo.game.turn.advanced"

var _bus: Node

func before() -> void:
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _format_date_text(year: int, month: int, day: int) -> String:
	return "Date: %04d-%02d-%02d" % [year, month, day]

func _hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(auto_free(hud))
	await get_tree().process_frame
	return hud

func _publish_turn_advanced(year: int, month: int, day: int, active_player_id: String) -> void:
	_bus.PublishSimple(
		EVENT_TURN_ADVANCED,
		"ut",
		"{\"GameId\":\"g1\",\"TurnNumber\":1,\"ActivePlayerId\":\"%s\",\"Year\":%d,\"Month\":%d,\"Day\":%d}" % [active_player_id, year, month, day]
	)

# ACC:T21.3
func test_date_label_updates_on_multiple_turn_advanced_events() -> void:
	var hud = await _hud()
	var date_label: Label = hud.get_node("TopBar/HBox/DateLabel")

	_publish_turn_advanced(3, 2, 1, "p1")
	await get_tree().process_frame
	assert_str(date_label.text).is_equal(_format_date_text(3, 2, 1))

	_publish_turn_advanced(3, 2, 2, "p1")
	await get_tree().process_frame
	assert_str(date_label.text).is_equal(_format_date_text(3, 2, 2))

	_publish_turn_advanced(3, 2, 3, "p1")
	await get_tree().process_frame
	assert_str(date_label.text).is_equal(_format_date_text(3, 2, 3))

# ACC:T21.3
func test_date_label_does_not_rollback_when_older_turn_advanced_event_arrives_late() -> void:
	var hud = await _hud()
	var date_label: Label = hud.get_node("TopBar/HBox/DateLabel")

	_publish_turn_advanced(3, 2, 10, "p1")
	await get_tree().process_frame
	var expected_latest := _format_date_text(3, 2, 10)
	assert_str(date_label.text).is_equal(expected_latest)

	_publish_turn_advanced(3, 2, 9, "p1")
	await get_tree().process_frame
	assert_str(date_label.text).is_equal(expected_latest)
