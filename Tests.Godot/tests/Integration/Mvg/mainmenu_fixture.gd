extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# MVG fixture for the Sanguo startup pilot. It uses focused Control nodes and
# InputEventAction, not direct business-method calls, as engine-input evidence.
const MAIN_SCENE := preload("res://Game.Godot/Scenes/Main.tscn")
const EVENT_BUS := preload("res://Game.Godot/Adapters/EventBusAdapter.cs")

const MENU_PATH := "MenuLayer/MainMenu"
const PLAY_PATH := "MenuRow/MenuBox/BtnPlay"
const START_PATH := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const CONFIG_PATH := "ConfigCenter/NewGameConfig"

var _main: Node
var _bus: Node
var _events: Array[Dictionary] = []

func before_test() -> void:
	_events = []
	_reset_named_root_node("EventBus")
	_reset_named_root_node("CompositionRoot")
	_bus = EVENT_BUS.new()
	_bus.name = "EventBus"
	get_tree().root.add_child(_bus)
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))
	_main = MAIN_SCENE.instantiate()
	add_child(_main)
	await get_tree().process_frame

func after_test() -> void:
	var release := InputEventAction.new()
	release.action = "ui_accept"
	release.pressed = false
	get_viewport().push_input(release)
	Input.action_release("ui_accept")
	if is_instance_valid(_main):
		_main.queue_free()
	if is_instance_valid(_bus):
		_bus.queue_free()
	await get_tree().process_frame

func _reset_named_root_node(node_name: String) -> void:
	var node := get_node_or_null("/root/" + node_name)
	if node != null:
		node.name = "%s__old__%s" % [node_name, str(Time.get_ticks_msec())]
		node.queue_free()

func _on_domain_event_emitted(type, source, data_json, id, spec, ct, ts) -> void:
	_events.append({
		"type": str(type),
		"source": str(source),
		"data_json": str(data_json),
		"id": str(id),
		"spec": str(spec),
		"ct": str(ct),
		"ts": str(ts),
	})

func _menu() -> Control:
	return _main.get_node(MENU_PATH) as Control

func _wait_for(condition: Callable, timeout_ms: int = 5000) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while not condition.call() and Time.get_ticks_msec() < deadline:
		await get_tree().process_frame
	if not condition.call():
		print("MVG_WAIT_TIMEOUT events=", _events)
		return false
	return true

func _has_event(event_type: String) -> bool:
	for event in _events:
		if str(event.get("type", "")) == event_type:
			return true
	return false

func _activate(button: Button) -> bool:
	if not is_instance_valid(button) or not button.is_visible_in_tree() or button.disabled:
		return false
	button.grab_focus()
	await get_tree().process_frame
	if not button.has_focus():
		return false
	var press := InputEventAction.new()
	press.action = "ui_accept"
	press.pressed = true
	button.get_viewport().push_input(press)
	await get_tree().process_frame
	var release := InputEventAction.new()
	release.action = "ui_accept"
	release.pressed = false
	button.get_viewport().push_input(release)
	await get_tree().process_frame
	return true
