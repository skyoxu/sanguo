extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _created_bus := false
var _main: Node
var _saw_settings_event := false

func before() -> void:
	_main = null
	_created_bus = false
	_saw_settings_event = false
	_bus = get_node_or_null("/root/EventBus")
	if _bus == null:
		_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
		_bus.name = "EventBus"
		get_tree().get_root().add_child(_bus)
		_created_bus = true
	if _bus != null and _bus.has_signal("DomainEventEmitted"):
		var callable := Callable(self, "_on_evt")
		if not _bus.is_connected("DomainEventEmitted", callable):
			_bus.connect("DomainEventEmitted", callable)

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	if str(type) == "ui.menu.settings":
		_saw_settings_event = true

func after() -> void:
	if _main != null and is_instance_valid(_main):
		_main.queue_free()
		_main = null
	if _created_bus and _bus != null and is_instance_valid(_bus):
		_bus.queue_free()
		_created_bus = false

# ACC:T29.8
func test_main_menu_settings_button_shows_settings_panel() -> void:
	_main = preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	_main.name = "Main"
	get_tree().get_root().add_child(_main)
	await get_tree().process_frame

	var panel := _main.get_node_or_null("SettingsLayer/SettingsPanel") as Control
	assert_bool(panel != null).is_true()
	if panel == null:
		return
	assert_bool(panel.visible).is_false()

	_saw_settings_event = false
	var btn := _main.get_node("MenuLayer/MainMenu/MenuRow/MenuBox/BtnSettings")
	btn.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(_saw_settings_event).is_true()
	assert_bool(panel.visible).is_true()
