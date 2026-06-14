extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

var _event_types: Array = []

func _on_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	_event_types.append(str(type))

# ACC:T215.2
func test_continue_without_valid_state_is_refused_and_keeps_menu_state() -> void:
	var bus := preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	bus.name = "EventBus"
	add_child(auto_free(bus))
	bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event"))
	_event_types = []

	var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(scene))
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(scene)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var load_button := MenuTestDriver.resolve_load_button(menu)
	var load_panel := MenuTestDriver.resolve_load_panel(menu)
	var status_label := MenuTestDriver.resolve_status_label(menu)
	assert_object(load_button).is_not_null()
	assert_object(load_panel).is_not_null()
	assert_object(status_label).is_not_null()
	if load_button == null or load_panel == null or status_label == null:
		return

	load_button.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(menu.visible).is_true()
	assert_bool(load_panel.visible).is_false()
	assert_bool(_event_types.has("ui.menu.load")).is_false()
	assert_bool(_event_types.has("ui.hud.load")).is_false()
	assert_bool(status_label.visible).is_true()
	assert_str(str(status_label.text).to_lower()).contains("unavailable")
