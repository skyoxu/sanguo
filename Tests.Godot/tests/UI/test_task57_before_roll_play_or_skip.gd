extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const UI_MENU_START := "ui.menu.start"
const UI_ACTION_CARD_SKIP := "ui.sanguo.action_card.skip"

const EVT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVT_ACTION_CARD_PLAYED := "core.sanguo.action_card.played"
const EVT_DICE_ROLLED := "core.sanguo.dice.rolled"

var _bus: Node
var _types: Array = []

func before_test() -> void:
	_types = []

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

	var controller := preload("res://Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs").new()
	controller.name = "SanguoGameLoopController__test__%s" % str(Time.get_ticks_msec())
	get_tree().get_root().add_child(auto_free(controller))

	_bus.call("PublishSimple", UI_MENU_START, "ui", "{}")
	await _wait_for_type(EVT_TURN_STARTED, 240)
	_types = []

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	if _types.size() < 256:
		_types.append(str(type))

func _wait_for_type(t: String, max_frames: int) -> bool:
	for _i in range(max_frames):
		if _types.has(t):
			return true
		await get_tree().process_frame
	return false

# ACC:T57.3
func test_before_roll_skip_does_not_emit_action_card_played() -> void:
	var payload := JSON.stringify({
		"PlayerId": "p1",
		"CorrelationId": "t57-skip-2",
		"CausationId": UI_ACTION_CARD_SKIP,
	})
	_bus.call("PublishSimple", UI_ACTION_CARD_SKIP, "ui", payload)

	var saw_dice := await _wait_for_type(EVT_DICE_ROLLED, 240)
	assert_bool(saw_dice).is_true()
	assert_bool(_types.has(EVT_ACTION_CARD_PLAYED)).is_false()
