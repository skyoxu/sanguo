extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

var _bus: Node
var _event_types: Array = []

func before() -> void:
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event"))
	_event_types = []

func _on_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	_event_types.append(str(type))

# ACC:T215.3
func test_continue_with_valid_state_resumes_run_without_bootstrap() -> void:
	var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(scene))
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(scene)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	_bus.PublishSimple("core.sanguo.game.saved", "ut", "{\"checkpoint\":\"turn-3\"}")
	await get_tree().process_frame

	var load_button := MenuTestDriver.resolve_load_button(menu)
	var load_panel := MenuTestDriver.resolve_load_panel(menu)
	assert_object(load_button).is_not_null()
	assert_object(load_panel).is_not_null()
	if load_button == null or load_panel == null:
		return

	_event_types = []
	load_button.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(_event_types.has("ui.menu.load")).is_true()
	assert_bool(_event_types.has("ui.hud.load")).is_true()
	assert_bool(_event_types.has("ui.menu.start")).is_false()
	assert_bool(load_panel.visible).is_true()

	_bus.PublishSimple("core.sanguo.game.loaded", "ut", "{\"checkpoint\":\"turn-3\"}")
	await get_tree().process_frame

	assert_bool(menu.visible).is_false()
	assert_bool(load_panel.visible).is_false()
