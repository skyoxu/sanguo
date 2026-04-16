extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_TYPE_MENU_START := "ui.menu.start"
const KEY_ACTIVE_STRATEGEM_ID := "active_strategem_id"
const KEY_PASSIVE_STRATEGEM_ID := "passive_strategem_id"

const PATH_BTN_PLAY := "MenuRow/MenuBox/BtnPlay"
const PATH_BTN_START := "ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart"
const PATH_ACTIVE_STRATEGEM_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/ActiveStrategemOption"
const PATH_PASSIVE_STRATEGEM_OPTION := "ConfigCenter/NewGameConfig/Margin/Root/TopRow/OptionsPanel/Margin/VBox/PassiveStrategemOption"

var _bus: Node
var _seen_menu_start := false
var _last_payload_json := ""

func before_test() -> void:
	_seen_menu_start = false
	_last_payload_json = ""

	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	var existing_cr := get_node_or_null("/root/CompositionRoot")
	if existing_cr != null:
		existing_cr.name = "CompositionRoot__old__%s" % str(Time.get_ticks_msec())
		existing_cr.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(_bus)
	_bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event_emitted"))

func after_test() -> void:
	if is_instance_valid(_bus):
		_bus.queue_free()

func _on_domain_event_emitted(type, _source, data_json, _id, _spec, _ct, _ts) -> void:
	if str(type) == EVENT_TYPE_MENU_START:
		_seen_menu_start = true
		_last_payload_json = str(data_json)

func _parse_json_dict(json_text: String) -> Dictionary:
	var text := json_text.strip_edges()
	if text == "":
		return {}
	var v: Variant = JSON.parse_string(text)
	if typeof(v) != TYPE_DICTIONARY:
		return {}
	return v as Dictionary

func _open_menu(menu: Node) -> Dictionary:
	var btn_play := menu.get_node(PATH_BTN_PLAY) as Button
	btn_play.emit_signal("pressed")
	await get_tree().process_frame
	return {
		"start": menu.get_node(PATH_BTN_START),
		"active": menu.get_node(PATH_ACTIVE_STRATEGEM_OPTION),
		"passive": menu.get_node(PATH_PASSIVE_STRATEGEM_OPTION),
	}

func _clear_option(option: OptionButton) -> void:
	option.clear()
	option.emit_signal("item_selected", -1)

func _press_start_and_wait(start_button: Button) -> void:
	_seen_menu_start = false
	_last_payload_json = ""
	start_button.emit_signal("pressed")
	for _i in range(120):
		if _seen_menu_start:
			break
		await get_tree().process_frame

# acceptance: ACC:T94.1
func test_task94_start_is_refused_when_active_strategem_is_missing() -> void:
	var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
	add_child(auto_free(menu))
	await get_tree().process_frame

	var nodes := await _open_menu(menu)
	var start_button: Button = nodes["start"]
	var active_option: OptionButton = nodes["active"]
	var passive_option: OptionButton = nodes["passive"]

	assert_int(active_option.item_count).is_greater(0)
	assert_int(passive_option.item_count).is_greater(0)
	_clear_option(active_option)
	await get_tree().process_frame

	assert_bool(start_button.disabled).is_true()
	await _press_start_and_wait(start_button)
	assert_bool(_seen_menu_start).is_false()

# acceptance: ACC:T94.1
func test_task94_start_payload_contains_active_and_passive_strategems_when_selected() -> void:
	var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
	add_child(auto_free(menu))
	await get_tree().process_frame

	var nodes := await _open_menu(menu)
	var start_button: Button = nodes["start"]
	var active_option: OptionButton = nodes["active"]
	var passive_option: OptionButton = nodes["passive"]

	assert_bool(start_button.disabled).is_false()
	assert_int(active_option.selected).is_greater_equal(0)
	assert_int(passive_option.selected).is_greater_equal(0)

	await _press_start_and_wait(start_button)
	assert_bool(_seen_menu_start).is_true()

	var payload := _parse_json_dict(_last_payload_json)
	assert_bool(payload.has(KEY_ACTIVE_STRATEGEM_ID)).is_true()
	assert_bool(payload.has(KEY_PASSIVE_STRATEGEM_ID)).is_true()
	assert_str(str(payload.get(KEY_ACTIVE_STRATEGEM_ID, ""))).is_not_empty()
	assert_str(str(payload.get(KEY_PASSIVE_STRATEGEM_ID, ""))).is_not_empty()
