extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const _SETTLEMENT_SCENE_PATH: String = "res://Game.Godot/Scenes/UI/SettlementScreen.tscn"
const _MAIN_MENU_SCENE_PATH: String = "res://Game.Godot/Scenes/UI/MainMenu.tscn"
const _GAME_ENDED_TYPE: String = "core.sanguo.game.ended"
const _GAME_ENDED_PAYLOAD_JSON: String = "{\"WinnerPlayerId\":\"p1\",\"EndReason\":\"max_turns\",\"StatsSnapshot\":{\"TurnNumber\":10,\"TreasuryMinorUnits\":0,\"Players\":[{\"PlayerId\":\"p1\",\"Money\":10000}]}}"

const _WINNER_LABEL_PATH: NodePath = NodePath("Center/Panel/VBox/WinnerLabel")
const _STATS_LABEL_PATH: NodePath = NodePath("Center/Panel/VBox/StatsSnapshotLabel")
const _MAIN_MENU_BUTTON_PATH: NodePath = NodePath("Center/Panel/VBox/Buttons/MainMenuButton")
const _NEW_GAME_BUTTON_PATH: NodePath = NodePath("Center/Panel/VBox/Buttons/NewGameButton")

var _bus: Node
var _received := false
var _etype := ""
var _main_menu: Control


func _parse_json_dict(json_text: String) -> Dictionary:
	var parsed = JSON.parse_string(json_text)
	assert_bool(typeof(parsed) == TYPE_DICTIONARY).is_true()
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed as Dictionary


func before() -> void:
	_received = false
	_etype = ""

	# Install a temporary EventBus under /root to mimic Autoload.
	var existing_bus = get_node_or_null("/root/EventBus")
	if existing_bus != null:
		existing_bus.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing_bus.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))
	_bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

	# Install a minimal Main/Menu tree to satisfy absolute NodePaths in SettlementScreen.
	var existing_main = get_node_or_null("/root/Main")
	if existing_main != null:
		existing_main.name = "Main__old__%s" % str(Time.get_ticks_msec())
		existing_main.queue_free()

	var main_root := Node.new()
	main_root.name = "Main"
	get_tree().get_root().add_child(auto_free(main_root))

	var menu_layer := CanvasLayer.new()
	menu_layer.name = "MenuLayer"
	main_root.add_child(auto_free(menu_layer))

	_main_menu = preload(_MAIN_MENU_SCENE_PATH).instantiate() as Control
	assert_object(_main_menu).is_not_null()
	if _main_menu == null:
		return
	_main_menu.name = "MainMenu"
	menu_layer.add_child(auto_free(_main_menu))
	_main_menu.visible = false


func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	_received = true
	_etype = str(type)


func _instantiate_settlement_screen() -> Control:
	var packed = load(_SETTLEMENT_SCENE_PATH)
	assert_object(packed).is_not_null()
	if packed == null:
		return null

	var scene: PackedScene = packed as PackedScene
	assert_object(scene).is_not_null()
	if scene == null:
		return null

	var node: Node = scene.instantiate()
	var screen: Control = node as Control
	assert_object(screen).is_not_null()
	if screen == null:
		return null

	add_child(auto_free(screen))
	return screen


# acceptance: ACC:T60.1
func test_task60_settlement_screen_is_hidden_before_event_and_shows_payload_after_event() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return
	assert_bool(screen.visible).is_false()

	var winner_label: Label = screen.get_node_or_null(_WINNER_LABEL_PATH) as Label
	assert_bool(winner_label != null).is_true()

	var stats_label: RichTextLabel = screen.get_node_or_null(_STATS_LABEL_PATH) as RichTextLabel
	assert_bool(stats_label != null).is_true()

	_bus.PublishSimple(_GAME_ENDED_TYPE, "gdunit", _GAME_ENDED_PAYLOAD_JSON)
	await get_tree().process_frame

	assert_bool(screen.visible).is_true()
	assert_str(winner_label.text).is_equal("p1")
	var stats := _parse_json_dict(stats_label.text)
	assert_int(int(stats.get("TurnNumber", -1))).is_equal(10)
	assert_int(int(stats.get("TreasuryMinorUnits", -1))).is_equal(0)
	assert_bool(stats.has("Players")).is_true()
	assert_int(int((stats.get("Players") as Array).size())).is_equal(1)
	assert_str(str(((stats.get("Players") as Array)[0] as Dictionary).get("PlayerId", ""))).is_equal("p1")

	_bus.PublishSimple(_GAME_ENDED_TYPE, "gdunit", "{\"WinnerPlayerId\":\"p2\",\"EndReason\":\"max_turns\",\"StatsSnapshot\":{\"TurnNumber\":99,\"TreasuryMinorUnits\":123,\"Players\":[{\"PlayerId\":\"p2\",\"Money\":777}]}}")
	await get_tree().process_frame

	assert_str(winner_label.text).is_equal("p2")
	var stats2 := _parse_json_dict(stats_label.text)
	assert_int(int(stats2.get("TurnNumber", -1))).is_equal(99)
	assert_int(int(stats2.get("TreasuryMinorUnits", -1))).is_equal(123)


# acceptance: ACC:T60.2
func test_task60_settlement_screen_main_menu_button_shows_main_menu_and_hides_screen() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	_bus.PublishSimple(_GAME_ENDED_TYPE, "gdunit", _GAME_ENDED_PAYLOAD_JSON)
	await get_tree().process_frame

	assert_bool(screen.visible).is_true()

	var main_menu_button: Button = screen.get_node_or_null(_MAIN_MENU_BUTTON_PATH) as Button
	assert_bool(main_menu_button != null).is_true()
	main_menu_button.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(screen.visible).is_false()
	assert_bool(_main_menu.visible).is_true()


# acceptance: ACC:T60.3
func test_task60_settlement_screen_new_game_returns_to_main_menu_and_clears_result_text() -> void:
	_received = false
	_etype = ""

	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	_bus.PublishSimple(_GAME_ENDED_TYPE, "gdunit", _GAME_ENDED_PAYLOAD_JSON)
	await get_tree().process_frame

	var winner_label: Label = screen.get_node_or_null(_WINNER_LABEL_PATH) as Label
	assert_bool(winner_label != null).is_true()
	var stats_label: RichTextLabel = screen.get_node_or_null(_STATS_LABEL_PATH) as RichTextLabel
	assert_bool(stats_label != null).is_true()

	assert_bool(screen.visible).is_true()
	assert_str(winner_label.text).is_equal("p1")
	var stats := _parse_json_dict(stats_label.text)
	assert_int(int(stats.get("TurnNumber", -1))).is_equal(10)

	_received = false
	_etype = ""
	_main_menu.visible = false
	var new_game_button: Button = screen.get_node_or_null(_NEW_GAME_BUTTON_PATH) as Button
	assert_bool(new_game_button != null).is_true()
	new_game_button.emit_signal("pressed")
	await get_tree().process_frame

	assert_bool(_main_menu.visible).is_true()
	assert_bool(screen.visible).is_false()
	assert_str(winner_label.text).is_equal("")
	assert_str(stats_label.text).is_equal("")


# acceptance: ACC:T60.4
func test_task60_settlement_screen_has_navigation_buttons() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	var main_menu_button: Button = screen.get_node_or_null(_MAIN_MENU_BUTTON_PATH) as Button
	assert_bool(main_menu_button != null).is_true()

	var new_game_button: Button = screen.get_node_or_null(_NEW_GAME_BUTTON_PATH) as Button
	assert_bool(new_game_button != null).is_true()


func test_task60_settlement_screen_ignores_non_game_ended_event_type() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	_bus.PublishSimple("core.sanguo.game.turn.started", "gdunit", "{\"ActivePlayerId\":\"p1\"}")
	await get_tree().process_frame

	assert_bool(screen.visible).is_false()


func test_task60_settlement_screen_remains_hidden_on_invalid_json_payload() -> void:
	var screen: Control = _instantiate_settlement_screen()
	if screen == null:
		return

	_bus.PublishSimple(_GAME_ENDED_TYPE, "gdunit", "{")
	await get_tree().process_frame

	assert_bool(screen.visible).is_false()
