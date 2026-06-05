extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_SCENE_CANDIDATES := [
	"res://Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn",
	"res://Game.Godot/Scenes/UI/MainMenu.tscn",
	"res://Game.Godot/scenes/ui/main_menu.tscn",
	"res://Scenes/UI/MainMenu.tscn",
	"res://scenes/ui/main_menu.tscn"
]

const BOOT_STATUS_PANEL_SCENE_CANDIDATES := [
	"res://Game.Godot/Scenes/UI/BootStatusPanel.tscn",
	"res://Game.Godot/scenes/ui/boot_status_panel.tscn",
	"res://Scenes/UI/BootStatusPanel.tscn",
	"res://scenes/ui/boot_status_panel.tscn"
]

const CONTINUE_GATE_DIALOG_SCENE_CANDIDATES := [
	"res://Game.Godot/Scenes/UI/ContinueGateDialog.tscn",
	"res://Game.Godot/scenes/ui/continue_gate_dialog.tscn",
	"res://Scenes/UI/ContinueGateDialog.tscn",
	"res://scenes/ui/continue_gate_dialog.tscn"
]

const GAME_OVER_FAIL_SCENE_CANDIDATES := [
	"res://Game.Godot/Scenes/UI/GameOverFailMenu.tscn",
	"res://Game.Godot/scenes/ui/game_over_fail_menu.tscn",
	"res://Scenes/UI/GameOverFailMenu.tscn",
	"res://scenes/ui/game_over_fail_menu.tscn"
]

func _instantiate_first_existing(candidates: Array) -> Node:
	for path in candidates:
		if ResourceLoader.exists(path):
			var resource := load(path)
			if resource is PackedScene:
				return resource.instantiate()
	return null

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

func _call_first_existing(node: Node, method_names: Array, args: Array = []) -> bool:
	for method_name in method_names:
		if node.has_method(method_name):
			node.callv(method_name, args)
			return true
	return false

func _set_boot_status(panel: Node, state: String, message: String) -> bool:
	if panel.has_method("set_boot_state"):
		panel.call("set_boot_state", state, message)
		return true
	return _call_first_existing(panel, ["set_progress", "show_progress", "report_progress", "update_progress"], [message])

func _request_blocked_continue(dialog: Node) -> bool:
	if dialog.has_method("set_menu_state"):
		dialog.call("set_menu_state", "main_menu")
	if dialog.has_method("request_continue"):
		return dialog.call("request_continue", false) == false
	if dialog.has_method("evaluate_continue_gate"):
		return dialog.call("evaluate_continue_gate", false) == false
	return _call_first_existing(dialog, ["block_continue", "show_blocked", "open_blocked", "set_continue_allowed"], [false])

func _has_adapter_event(node: Node, event_name: String) -> bool:
	if not node.has_method("get_adapter_event_names"):
		return false
	var events: Variant = node.call("get_adapter_event_names")
	return events is Array and (events as Array).has(event_name)

func _is_visible_canvas_item(node: Node) -> bool:
	if node is CanvasItem:
		return (node as CanvasItem).visible
	return false

# acceptance: ACC:T198.1
# MainMenu must be a standalone player-visible screen that survives load and first interaction.
func test_main_menu_loads_as_independent_screen_and_handles_first_interaction() -> void:
	var menu := _instantiate_first_existing(MAIN_MENU_SCENE_CANDIDATES)
	assert_that(menu).is_not_null()
	add_child(menu)
	await get_tree().process_frame
	assert_that(menu.is_inside_tree()).is_true()
	assert_that(_is_visible_canvas_item(menu)).is_true()
	var first_action := _find_node_by_names(menu, ["ContinueButton", "LoadButton", "BtnLoad", "NewGameButton", "StartButton", "BtnPlay", "QuitButton", "BtnQuit"])
	if first_action != null:
		_press_if_possible(first_action)
	elif menu.has_method("get_entry_state"):
		assert_that(str(menu.call("get_entry_state"))).is_equal("boot_menu_entry")
	await get_tree().process_frame
	assert_that(menu.is_inside_tree()).is_true()

# acceptance: ACC:T198.2
# acceptance: ACC:T198.3
# Continue-related actions must be visible, and unavailable continue must stay blocked.
func test_main_menu_exposes_continue_actions_and_blocks_unavailable_continue() -> void:
	var menu := _instantiate_first_existing(MAIN_MENU_SCENE_CANDIDATES)
	assert_that(menu).is_not_null()
	add_child(menu)
	await get_tree().process_frame
	var continue_action := _find_node_by_names(menu, ["ContinueButton", "ResumeButton", "LoadButton", "ContinueAction", "BtnLoad"])
	assert_that(continue_action != null or _has_adapter_event(menu, "menu_entry_requested")).is_true()
	var before_child_count := get_tree().root.get_child_count()
	var before_visible: bool = _is_visible_canvas_item(menu)
	if continue_action != null:
		_press_if_possible(continue_action)
	await get_tree().process_frame
	assert_that(get_tree().root.get_child_count()).is_equal(before_child_count)
	assert_that(_is_visible_canvas_item(menu)).is_equal(before_visible)
	_free_nodes([menu])

# acceptance: ACC:T198.4
# BootStatusPanel must expose player-visible boot progress state.
func test_boot_status_panel_reports_progress_state() -> void:
	var panel := _instantiate_first_existing(BOOT_STATUS_PANEL_SCENE_CANDIDATES)
	assert_that(panel).is_not_null()
	add_child(panel)
	await get_tree().process_frame
	var changed := _set_boot_status(panel, "progress", "Boot progress 50%")
	assert_that(changed).is_true()
	await get_tree().process_frame
	var text := _visible_text(panel)
	assert_that(text.contains("progress") or text.contains("loading") or text.contains("50") or text.contains("boot")).is_true()
	_free_nodes([panel])

# acceptance: ACC:T198.5
# BootStatusPanel must expose player-visible successful boot state.
func test_boot_status_panel_reports_success_state() -> void:
	var panel := _instantiate_first_existing(BOOT_STATUS_PANEL_SCENE_CANDIDATES)
	assert_that(panel).is_not_null()
	add_child(panel)
	await get_tree().process_frame
	var changed := _set_boot_status(panel, "ready", "Boot complete")
	assert_that(changed).is_true()
	await get_tree().process_frame
	var text := _visible_text(panel)
	assert_that(text.contains("success") or text.contains("ready") or text.contains("complete") or text.contains("started")).is_true()
	_free_nodes([panel])

# acceptance: ACC:T198.6
# BootStatusPanel must expose player-visible boot failure state.
func test_boot_status_panel_reports_failure_state() -> void:
	var panel := _instantiate_first_existing(BOOT_STATUS_PANEL_SCENE_CANDIDATES)
	assert_that(panel).is_not_null()
	add_child(panel)
	await get_tree().process_frame
	var changed := _set_boot_status(panel, "failure", "Save unavailable")
	assert_that(changed).is_true()
	await get_tree().process_frame
	var text := _visible_text(panel)
	assert_that(text.contains("fail") or text.contains("error") or text.contains("unavailable")).is_true()
	_free_nodes([panel])

# acceptance: ACC:T198.7
# ContinueGateDialog must block continue and keep menu state unchanged until dismissal or resolution.
func test_continue_gate_dialog_blocks_continue_and_preserves_menu_state() -> void:
	var menu := _instantiate_first_existing(MAIN_MENU_SCENE_CANDIDATES)
	var dialog := _instantiate_first_existing(CONTINUE_GATE_DIALOG_SCENE_CANDIDATES)
	assert_that(menu).is_not_null()
	assert_that(dialog).is_not_null()
	add_child(menu)
	add_child(dialog)
	await get_tree().process_frame
	var before_visible_text := _visible_text(menu)
	var blocked := _request_blocked_continue(dialog)
	assert_that(blocked).is_true()
	await get_tree().process_frame
	assert_that(_visible_text(menu)).is_equal(before_visible_text)
	assert_that(menu.is_inside_tree()).is_true()
	_free_nodes([dialog, menu])

# acceptance: ACC:T198.9
# Game-over failure must provide a player-visible route back to the main menu surface.
func test_game_over_failure_surface_exposes_main_menu_route() -> void:
	var surface := _instantiate_first_existing(GAME_OVER_FAIL_SCENE_CANDIDATES)
	assert_that(surface).is_not_null()
	add_child(surface)
	await get_tree().process_frame
	var main_menu_action := _find_node_by_names(surface, ["MainMenuButton", "ReturnToMenuButton", "BackToMainMenuButton"])
	assert_that(main_menu_action).is_not_null()
	assert_bool(surface.has_method("get_route_requested")).is_true()
	assert_bool(surface.call("get_route_requested")).is_false()
	_press_if_possible(main_menu_action)
	await get_tree().process_frame
	assert_bool(surface.call("get_route_requested")).is_true()
	if surface.has_method("to_contract_payload"):
		var payload: Dictionary = surface.call("to_contract_payload")
		assert_bool(bool(payload.get("route_requested", false))).is_true()
		assert_str(str(payload.get("surface", ""))).is_equal("GameOverFailMenu")
	assert_bool(_has_adapter_event(surface, "main_menu_requested")).is_true()
	assert_that(surface.is_inside_tree()).is_true()
	_free_nodes([surface])

# acceptance: ACC:T198.10
# Godot-side coverage must exercise MainMenu player-visible behavior.
func test_main_menu_player_visible_actions_are_discoverable() -> void:
	var menu := _instantiate_first_existing(MAIN_MENU_SCENE_CANDIDATES)
	assert_that(menu).is_not_null()
	add_child(menu)
	await get_tree().process_frame
	var has_start_action := _find_node_by_names(menu, ["NewGameButton", "StartButton", "BtnPlay"]) != null
	var has_continue_action := _find_node_by_names(menu, ["ContinueButton", "ResumeButton", "LoadButton", "BtnLoad"]) != null
	assert_that(has_start_action or _has_adapter_event(menu, "menu_entry_requested")).is_true()
	assert_that(has_continue_action or _has_adapter_event(menu, "menu_entry_requested")).is_true()
	_free_nodes([menu])

# acceptance: ACC:T198.11
# Godot-side coverage must exercise BootStatusPanel player-visible behavior.
func test_boot_status_panel_player_visible_status_text_changes_between_states() -> void:
	var panel := _instantiate_first_existing(BOOT_STATUS_PANEL_SCENE_CANDIDATES)
	assert_that(panel).is_not_null()
	add_child(panel)
	await get_tree().process_frame
	_set_boot_status(panel, "progress", "Boot progress 25%")
	await get_tree().process_frame
	var progress_text := _visible_text(panel)
	_set_boot_status(panel, "failure", "Boot failed")
	await get_tree().process_frame
	assert_that(_visible_text(panel)).is_not_equal(progress_text)
	_free_nodes([panel])

# acceptance: ACC:T198.12
# Godot-side coverage must exercise ContinueGateDialog player-visible behavior.
func test_continue_gate_dialog_player_visible_block_message_is_observable() -> void:
	var dialog := _instantiate_first_existing(CONTINUE_GATE_DIALOG_SCENE_CANDIDATES)
	assert_that(dialog).is_not_null()
	add_child(dialog)
	await get_tree().process_frame
	var changed := _request_blocked_continue(dialog)
	assert_that(changed).is_true()
	await get_tree().process_frame
	var text := _visible_text(dialog)
	assert_that(text.contains("continue") or text.contains("blocked") or text.contains("unavailable") or text.contains("save")).is_true()
	_free_nodes([dialog])

# acceptance: ACC:T198.13
# Godot-side coverage must exercise game-over failure player-visible behavior.
func test_game_over_failure_surface_reports_failed_outcome() -> void:
	var surface := _instantiate_first_existing(GAME_OVER_FAIL_SCENE_CANDIDATES)
	assert_that(surface).is_not_null()
	add_child(surface)
	await get_tree().process_frame
	var text := _visible_text(surface)
	assert_that(text.contains("game over") or text.contains("defeat") or text.contains("failed") or text.contains("failure")).is_true()
	_free_nodes([surface])

# acceptance: ACC:T198.14
# Adapter-facing UI must not embed domain resolution into the MainMenu script surface.
func test_main_menu_does_not_expose_domain_resolution_methods() -> void:
	var menu := _instantiate_first_existing(MAIN_MENU_SCENE_CANDIDATES)
	assert_that(menu).is_not_null()
	add_child(menu)
	await get_tree().process_frame
	assert_that(menu.has_method("resolve_domain_turn") or menu.has_method("calculate_game_over") or menu.has_method("mutate_campaign_state")).is_false()
	_free_nodes([menu])

# acceptance: ACC:T198.15
# Adapter-facing UI must keep ContinueGateDialog as a gate rather than silently starting gameplay.
func test_continue_gate_dialog_refuses_silent_gameplay_start_when_blocked() -> void:
	var dialog := _instantiate_first_existing(CONTINUE_GATE_DIALOG_SCENE_CANDIDATES)
	assert_that(dialog).is_not_null()
	add_child(dialog)
	await get_tree().process_frame
	var before_child_count := get_tree().root.get_child_count()
	_request_blocked_continue(dialog)
	_press_if_possible(_find_node_by_names(dialog, ["ContinueButton", "ConfirmButton", "ResumeButton"]))
	await get_tree().process_frame
	assert_that(get_tree().root.get_child_count()).is_equal(before_child_count)
	_free_nodes([dialog])

# acceptance: ACC:T198.16
# Adapter-facing UI must preserve deterministic boundaries for boot status reporting.
func test_boot_status_panel_does_not_expose_domain_mutation_methods() -> void:
	var panel := _instantiate_first_existing(BOOT_STATUS_PANEL_SCENE_CANDIDATES)
	assert_that(panel).is_not_null()
	add_child(panel)
	await get_tree().process_frame
	assert_that(panel.has_method("load_campaign_save") or panel.has_method("write_save_file") or panel.has_method("advance_domain_state")).is_false()
	_free_nodes([panel])
