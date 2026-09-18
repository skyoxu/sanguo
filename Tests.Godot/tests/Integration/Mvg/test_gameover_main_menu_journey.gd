extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const GAME_OVER_FAIL_SCENE_PATH := "res://Game.Godot/Scenes/UI/GameOverFailMenu.tscn"
const MAIN_MENU_SCENE_PATH := "res://Game.Godot/Scenes/UI/MainMenu.tscn"
const CONTINUE_GATE_DIALOG_SCENE_PATH := "res://Game.Godot/Scenes/UI/ContinueGateDialog.tscn"

func _instantiate(path: String) -> Node:
	assert_bool(ResourceLoader.exists(path)).is_true()
	var packed := load(path)
	assert_bool(packed is PackedScene).is_true()
	return (packed as PackedScene).instantiate()

func _activate(button: BaseButton) -> bool:
	if not is_instance_valid(button) or not button.is_visible_in_tree() or button.disabled:
		return false
	button.grab_focus()
	await get_tree().process_frame
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

func _free(nodes: Array) -> void:
	for node in nodes:
		if is_instance_valid(node):
			if node is Window:
				(node as Window).hide()
			node.queue_free()

func test_gameover_engine_action_requests_main_menu_and_preserves_continue_gate() -> void:
	var game_over := _instantiate(GAME_OVER_FAIL_SCENE_PATH)
	var main_menu := _instantiate(MAIN_MENU_SCENE_PATH)
	var continue_gate := _instantiate(CONTINUE_GATE_DIALOG_SCENE_PATH)
	add_child(game_over)
	add_child(main_menu)
	add_child(continue_gate)
	await get_tree().process_frame

	var button := game_over.find_child("MainMenuButton", true, false) as BaseButton
	assert_that(button).is_not_null()
	if OS.get_environment("MVG_INPUT_CHALLENGE") == "disconnect-main-menu-input":
		for connection in button.pressed.get_connections():
			button.pressed.disconnect(connection["callable"])

	assert_bool(await _activate(button)).is_true()
	await get_tree().process_frame
	var routed := bool(game_over.call("get_route_requested"))
	assert_bool(routed).override_failure_message("MVG_MAIN_MENU_INPUT_DID_NOT_ROUTE").is_true()
	assert_bool(main_menu.is_inside_tree()).is_true()

	continue_gate.call("set_menu_state", "game_over_failure")
	var accepted: bool = continue_gate.call("request_continue", false)
	assert_bool(accepted).is_false()
	assert_bool(bool((continue_gate.call("to_contract_payload") as Dictionary).get("gate_satisfied", true))).is_false()
	_free([continue_gate, main_menu, game_over])
