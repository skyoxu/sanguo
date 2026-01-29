extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const _GDUNIT_TOOLS = preload("res://addons/gdUnit4/src/core/GdUnitTools.gd")

var _bus: Node
var _tracked_nodes: Array = []

func _setup_event_bus() -> void:
	_tracked_nodes.clear()
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		await _GDUNIT_TOOLS.free_instance(existing)

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(_bus)
	_tracked_nodes.append(_bus)

func _connect_domain_event_emitted(handler: Callable) -> void:
	if _bus == null:
		return
	if _bus.is_connected("DomainEventEmitted", handler):
		return
	_bus.connect("DomainEventEmitted", handler)

func _teardown_event_bus() -> void:
	for node in _tracked_nodes:
		if is_instance_valid(node):
			await _GDUNIT_TOOLS.free_instance(node)
	_tracked_nodes.clear()

func _hud() -> Node:
	var hud = preload("res://Game.Godot/Scenes/UI/HUD.tscn").instantiate()
	add_child(hud)
	_tracked_nodes.append(hud)
	await get_tree().process_frame
	return hud
