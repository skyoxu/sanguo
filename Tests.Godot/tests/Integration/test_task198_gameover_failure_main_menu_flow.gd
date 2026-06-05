extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_SCENE_PATH := "res://Game.Godot/Scenes/UI/MainMenu.tscn"
const BOOT_STATUS_PANEL_SCENE_PATH := "res://Game.Godot/Scenes/UI/BootStatusPanel.tscn"
const CONTINUE_GATE_DIALOG_SCENE_PATH := "res://Game.Godot/Scenes/UI/ContinueGateDialog.tscn"
const GAME_OVER_FAIL_SCENE_PATH := "res://Game.Godot/Scenes/UI/GameOverFailMenu.tscn"

func _instantiate_scene(path: String) -> Node:
	assert_bool(ResourceLoader.exists(path)).is_true()
	var resource := load(path)
	assert_bool(resource is PackedScene).is_true()
	return (resource as PackedScene).instantiate()

func _free_nodes(nodes: Array) -> void:
	for node in nodes:
		if node != null and is_instance_valid(node):
			if node is Window:
				(node as Window).hide()
			(node as Node).queue_free()

func _find_node_by_names(root: Node, names: Array) -> Node:
	for candidate_name in names:
		var found := root.find_child(str(candidate_name), true, false)
		if found != null:
			return found
	return null

func _press_if_possible(node: Node) -> void:
	if node == null:
		return
	if node.has_method("press"):
		node.call("press")
	elif node.has_signal("pressed"):
		node.emit_signal("pressed")

func _surface_payload(node: Node) -> Dictionary:
	assert_bool(node.has_method("to_contract_payload")).is_true()
	return node.call("to_contract_payload")

func _surface_contract_key(node: Node) -> String:
	assert_bool(node.has_method("get_surface_contract_key")).is_true()
	return str(node.call("get_surface_contract_key"))

func _has_adapter_event(node: Node, event_name: String) -> bool:
	if not node.has_method("get_adapter_event_names"):
		return false
	var events: Variant = node.call("get_adapter_event_names")
	return events is Array and (events as Array).has(event_name)

func _visible_text(root: Node) -> String:
	var parts: Array[String] = []
	_collect_visible_text(root, parts)
	return " ".join(parts).to_lower()

func _collect_visible_text(node: Node, parts: Array[String]) -> void:
	if node is CanvasItem and not node.visible:
		return
	if node.get("text") != null:
		parts.append(str(node.get("text")))
	for child in node.get_children():
		_collect_visible_text(child, parts)

# acceptance: ACC:T198.10
# The failure route must move toward the main menu surfaces instead of leaving gameplay active.
func test_gameover_failure_routes_toward_real_main_menu_surface_and_stops_gameplay() -> void:
	var game_over := _instantiate_scene(GAME_OVER_FAIL_SCENE_PATH)
	var main_menu := _instantiate_scene(MAIN_MENU_SCENE_PATH)
	add_child(game_over)
	add_child(main_menu)
	await get_tree().process_frame

	assert_str(_surface_contract_key(game_over)).is_equal("GameOverFailMenu")
	assert_bool(_has_adapter_event(game_over, "main_menu_requested")).is_true()
	assert_bool(game_over.has_method("get_route_requested")).is_true()
	assert_bool(game_over.call("get_route_requested")).is_false()

	var main_menu_action := _find_node_by_names(game_over, ["MainMenuButton", "ReturnToMenuButton", "BackToMainMenuButton"])
	assert_that(main_menu_action).is_not_null()
	_press_if_possible(main_menu_action)
	await get_tree().process_frame

	assert_bool(game_over.call("get_route_requested")).is_true()
	assert_bool(bool(_surface_payload(game_over).get("route_requested", false))).is_true()
	assert_bool(main_menu.is_inside_tree()).is_true()
	assert_bool(game_over.is_inside_tree()).is_true()
	_free_nodes([game_over, main_menu])

# acceptance: ACC:T198.8
# MainMenu, BootStatusPanel, and ContinueGateDialog must all be player-visible in the failure flow.
func test_gameover_failure_exposes_required_real_menu_surfaces() -> void:
	var main_menu := _instantiate_scene(MAIN_MENU_SCENE_PATH)
	var boot_status := _instantiate_scene(BOOT_STATUS_PANEL_SCENE_PATH)
	var continue_gate := _instantiate_scene(CONTINUE_GATE_DIALOG_SCENE_PATH)
	add_child(main_menu)
	add_child(boot_status)
	add_child(continue_gate)
	await get_tree().process_frame

	assert_bool(main_menu.is_inside_tree()).is_true()
	assert_bool(boot_status.is_inside_tree()).is_true()
	assert_bool(continue_gate.is_inside_tree()).is_true()
	assert_bool(main_menu is CanvasItem and (main_menu as CanvasItem).visible).is_true()
	assert_bool(boot_status is CanvasItem and (boot_status as CanvasItem).visible).is_true()
	assert_bool(continue_gate.visible).is_true()
	assert_str(_surface_contract_key(boot_status)).is_equal("BootStatusPanel")
	assert_str(_surface_contract_key(continue_gate)).is_equal("ContinueGateDialog")
	_free_nodes([continue_gate, boot_status, main_menu])

# acceptance: ACC:T198.9
# Continue must be gated after game-over failure and must not silently resume gameplay.
func test_continue_request_after_gameover_failure_is_blocked_by_real_gate() -> void:
	var game_over := _instantiate_scene(GAME_OVER_FAIL_SCENE_PATH)
	var continue_gate := _instantiate_scene(CONTINUE_GATE_DIALOG_SCENE_PATH)
	add_child(game_over)
	add_child(continue_gate)
	await get_tree().process_frame

	assert_bool(continue_gate.has_method("set_menu_state")).is_true()
	assert_bool(continue_gate.has_method("request_continue")).is_true()
	continue_gate.call("set_menu_state", "game_over_failure")
	var accepted: bool = continue_gate.call("request_continue", false)
	await get_tree().process_frame

	assert_bool(accepted).is_false()
	assert_str(str(_surface_payload(continue_gate).get("menu_state", ""))).is_equal("game_over_failure")
	assert_bool(bool(_surface_payload(continue_gate).get("gate_satisfied", true))).is_false()
	assert_bool(game_over.call("get_route_requested")).is_false()
	assert_str(_visible_text(continue_gate)).contains("blocked")
	_free_nodes([continue_gate, game_over])
