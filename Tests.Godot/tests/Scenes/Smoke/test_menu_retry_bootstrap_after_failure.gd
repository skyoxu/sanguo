extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MenuTestDriver = preload("res://tests/Scenes/Smoke/_fixtures/test_menu_driver_fixture.gd")

var _bus: Node
var _event_types: Array = []
var _start_failed_payload := ""

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
	_start_failed_payload = ""

	var existing_root = get_node_or_null("/root/CompositionRoot")
	if existing_root != null:
		existing_root.name = "CompositionRoot__old__%s" % str(Time.get_ticks_msec())
		existing_root.queue_free()

	var composition_root = Node.new()
	composition_root.name = "CompositionRoot"
	get_tree().get_root().add_child(auto_free(composition_root))

	var loader = preload("res://Game.Godot/Adapters/TestFailingResourceLoader.cs").new()
	loader.name = "ResourceLoaderPort"
	composition_root.add_child(auto_free(loader))

func _on_domain_event(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	var event_type := str(type)
	_event_types.append(event_type)
	if event_type == "ui.menu.start.failed":
		_start_failed_payload = str(_data_json)

# ACC:T215.4
func test_retry_bootstrap_after_startup_failure_republishes_start() -> void:
	var scene := preload("res://Game.Godot/Scenes/Main.tscn").instantiate()
	add_child(auto_free(scene))
	await get_tree().process_frame

	var menu := MenuTestDriver.resolve_menu(scene)
	assert_object(menu).is_not_null()
	if menu == null:
		return

	var play_button := MenuTestDriver.resolve_play_button(menu)
	var start_button := MenuTestDriver.resolve_start_button(menu)
	var status_label := MenuTestDriver.resolve_status_label(menu)
	assert_object(play_button).is_not_null()
	assert_object(start_button).is_not_null()
	assert_object(status_label).is_not_null()
	if play_button == null or start_button == null or status_label == null:
		return

	play_button.emit_signal("pressed")
	await get_tree().process_frame

	start_button.emit_signal("pressed")
	for _i in range(120):
		if _event_types.has("ui.menu.start.failed"):
			break
		await get_tree().process_frame

	assert_bool(menu.visible).is_true()
	assert_bool(status_label.visible).is_true()
	assert_bool(_event_types.has("ui.menu.start")).is_true()
	assert_bool(_event_types.has("ui.menu.start.failed")).is_true()
	assert_bool(_start_failed_payload.length() > 0).is_true()
	assert_str(str(status_label.text).to_lower()).contains("failed")
	var retry_text := str(start_button.text).to_lower()
	assert_bool(retry_text.contains("retry") or retry_text.contains("restart")).is_true()

	_event_types = []
	start_button.emit_signal("pressed")
	for _i in range(120):
		if _event_types.has("ui.menu.start.failed"):
			break
		await get_tree().process_frame

	assert_bool(_event_types.has("ui.menu.start")).is_true()
	assert_bool(status_label.visible).is_true()
	assert_bool(_event_types.has("ui.menu.start.failed")).is_true()
	assert_str(str(status_label.text).to_lower()).contains("failed")
