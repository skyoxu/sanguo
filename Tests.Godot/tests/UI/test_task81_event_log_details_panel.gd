extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const _GDUNIT_TOOLS = preload("res://addons/gdUnit4/src/core/GdUnitTools.gd")
const CITY_BOUGHT_TYPE := "core.sanguo.city.bought"
const TURN_ADVANCED_TYPE := "core.sanguo.game.turn.advanced"

var _bus: Node
var _tracked_nodes: Array = []

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _setup_event_bus() -> void:
	_tracked_nodes.clear()
	var existing = get_node_or_null("/root/EventBus")
	if existing != null:
		await _GDUNIT_TOOLS.free_instance(existing)

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(_bus)
	_tracked_nodes.append(_bus)

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

func _wait_for_popup_log_commit(popup: Control, popup_message: Label, log_list: ItemList, max_frames: int = 30) -> void:
	for _i in range(max_frames):
		if log_list.get_item_count() > 0 and popup.visible and String(popup_message.text).strip_edges().length() > 0:
			return
		await get_tree().process_frame

# ACC:T81.1
# RED-FIRST: popup-log atomic commit for A-008 requires popup-capable events to update popup and log together.
func test_task81_city_bought_commits_popup_and_log_atomically() -> void:
	var hud = await _hud()
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.visible = true
	popup.visible = false
	popup_message.text = ""
	log_list.clear()

	_bus.PublishSimple(
		CITY_BOUGHT_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":100}"
	)

	var committed := false
	for _i in range(30):
		await get_tree().process_frame
		var has_log := log_list.get_item_count() > 0
		var has_popup := popup.visible and String(popup_message.text).strip_edges().length() > 0
		assert_bool(has_log == has_popup).is_true()
		if has_log and has_popup:
			committed = true
			break

	assert_bool(committed).is_true()
	assert_int(log_list.get_item_count()).is_equal(1)
	var log_summary := String(log_list.get_item_text(0)).strip_edges()
	var popup_text := String(popup_message.text).strip_edges()
	assert_bool(log_summary.length() > 0).is_true()
	assert_bool(popup.visible).is_true()
	assert_bool(popup_text.length() > 0).is_true()
	assert_str(log_summary).not_contains(CITY_BOUGHT_TYPE)

# ACC:T81.2
# RED-FIRST: non-popup events may append log but must not mutate ResultPopup state.
func test_task81_non_popup_event_keeps_result_popup_unchanged() -> void:
	var hud = await _hud()
	var popup: Control = hud.get_node("EventResultPopup")
	var popup_message: Label = popup.get_node("Center/Panel/VBox/Message")
	var event_log_panel: Control = hud.get_node("EventLogPanel")
	var log_list: ItemList = hud.get_node("EventLogPanel/Margin/VBox/EventList")

	event_log_panel.visible = true
	popup.visible = false
	popup_message.text = ""
	log_list.clear()

	_bus.PublishSimple(
		TURN_ADVANCED_TYPE,
		"ut",
		"{\"GameId\":\"g1\",\"ActivePlayerId\":\"p1\",\"TurnNumber\":2,\"Year\":3,\"Month\":2,\"Day\":2}"
	)

	for _i in range(20):
		await get_tree().process_frame
		assert_bool(popup.visible).is_false()
		assert_str(String(popup_message.text)).is_empty()
		if log_list.get_item_count() > 0:
			break

	assert_int(log_list.get_item_count()).is_equal(1)
	assert_bool(popup.visible).is_false()
	assert_str(String(popup_message.text)).is_empty()
