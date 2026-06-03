extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_PATHS := [
	"res://Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn",
	"res://Scenes/UI/MainMenu.tscn",
	"res://scenes/ui/MainMenu.tscn",
	"res://Game.Godot/Scenes/UI/MainMenu.tscn"
]
const BOOT_STATUS_PANEL_PATHS := [
	"res://Scenes/UI/BootStatusPanel.tscn",
	"res://scenes/ui/BootStatusPanel.tscn",
	"res://Game.Godot/Scenes/UI/BootStatusPanel.tscn"
]
const CONTINUE_GATE_DIALOG_PATHS := [
	"res://Scenes/UI/ContinueGateDialog.tscn",
	"res://scenes/ui/ContinueGateDialog.tscn",
	"res://Game.Godot/Scenes/UI/ContinueGateDialog.tscn"
]

func _load_first_scene(paths: Array) -> PackedScene:
	for path in paths:
		if ResourceLoader.exists(path):
			var resource: Resource = load(path)
			if resource is PackedScene:
				return resource
	return null

func _instantiate_scene(paths: Array) -> Node:
	var scene: PackedScene = _load_first_scene(paths)
	assert_that(scene).is_not_null()
	if scene == null:
		return null
	return scene.instantiate()

func _call_required(surface: Object, method_name: String, args: Array = []) -> Variant:
	var resolved_method := method_name
	if not surface.has_method(resolved_method):
		var alias := _method_alias(method_name)
		if surface.has_method(alias):
			resolved_method = alias
	assert_that(surface.has_method(resolved_method)).is_true()
	if not surface.has_method(resolved_method):
		return null
	return surface.callv(resolved_method, args)

func _method_alias(method_name: String) -> String:
	match method_name:
		"get_entry_state":
			return "GetEntryState"
		"get_surface_contract_key":
			return "GetSurfaceContractKey"
		"get_adapter_event_names":
			return "GetAdapterEventNames"
		_:
			return method_name

# acceptance: ACC:T192.1
func test_requirement_5187ab7a9fc0_exposes_main_menu_entry_surface() -> void:
	var main_menu: Node = _instantiate_scene(MAIN_MENU_PATHS)
	if main_menu == null:
		return
	assert_that(main_menu.visible).is_true()
	var entry_state: Variant = _call_required(main_menu, "get_entry_state")
	assert_that(entry_state).is_equal("boot_menu_entry")
	main_menu.queue_free()

# acceptance: ACC:T192.2
func test_requirement_f2066975f93c_exposes_boot_status_as_independent_surface() -> void:
	var panel: Node = _instantiate_scene(BOOT_STATUS_PANEL_PATHS)
	if panel == null:
		return
	assert_that(panel.visible).is_true()
	var status_text := str(_call_required(panel, "get_status_text"))
	assert_that(status_text.strip_edges().length()).is_greater(0)
	panel.queue_free()

# acceptance: ACC:T192.3
func test_requirement_61e0a6902857_exposes_continue_gate_as_independent_surface() -> void:
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if dialog == null:
		return
	assert_that(dialog.visible).is_true()
	var result: Variant = _call_required(dialog, "evaluate_continue_gate", [true])
	assert_that(result).is_equal(true)
	dialog.queue_free()

# acceptance: ACC:T192.4
func test_requirement_71589cb62f34_surfaces_report_type_shaped_wiring_contracts() -> void:
	var main_menu: Node = _instantiate_scene(MAIN_MENU_PATHS)
	var panel: Node = _instantiate_scene(BOOT_STATUS_PANEL_PATHS)
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if main_menu == null or panel == null or dialog == null:
		return
	assert_that(_call_required(main_menu, "get_surface_contract_key")).is_equal("MainMenu")
	assert_that(_call_required(panel, "get_surface_contract_key")).is_equal("BootStatusPanel")
	assert_that(_call_required(dialog, "get_surface_contract_key")).is_equal("ContinueGateDialog")
	main_menu.queue_free()
	panel.queue_free()
	dialog.queue_free()

# acceptance: ACC:T192.5
func test_main_menu_standalone_boot_entry_does_not_instantiate_unrelated_surfaces() -> void:
	var main_menu: Node = _instantiate_scene(MAIN_MENU_PATHS)
	if main_menu == null:
		return
	assert_that(main_menu.find_child("BootStatusPanel", true, false)).is_null()
	assert_that(main_menu.find_child("ContinueGateDialog", true, false)).is_null()
	assert_that(_call_required(main_menu, "get_entry_state")).is_equal("boot_menu_entry")
	main_menu.queue_free()

# acceptance: ACC:T192.6
func test_boot_status_panel_changes_display_when_boot_state_changes() -> void:
	var panel: Node = _instantiate_scene(BOOT_STATUS_PANEL_PATHS)
	if panel == null:
		return
	_call_required(panel, "set_boot_state", ["blocked", "Missing save index"])
	var blocked_text := str(_call_required(panel, "get_status_text"))
	_call_required(panel, "set_boot_state", ["ready", "Ready to continue"])
	var ready_text := str(_call_required(panel, "get_status_text"))
	assert_that(blocked_text).contains("Missing save index")
	assert_that(ready_text).contains("Ready to continue")
	assert_that(ready_text).is_not_equal(blocked_text)
	panel.queue_free()

# acceptance: ACC:T192.7
func test_continue_gate_dialog_refuses_continue_when_gate_is_not_satisfied() -> void:
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if dialog == null:
		return
	_call_required(dialog, "set_menu_state", ["main_menu"])
	var allowed: Variant = _call_required(dialog, "request_continue", [false])
	assert_that(allowed).is_equal(false)
	assert_that(_call_required(dialog, "get_menu_state")).is_equal("main_menu")
	dialog.queue_free()

# acceptance: ACC:T192.8
func test_player_visible_surfaces_have_adapter_facing_behavior_coverage() -> void:
	var main_menu: Node = _instantiate_scene(MAIN_MENU_PATHS)
	var panel: Node = _instantiate_scene(BOOT_STATUS_PANEL_PATHS)
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if main_menu == null or panel == null or dialog == null:
		return
	assert_array(_call_required(main_menu, "get_adapter_event_names")).contains("menu_entry_requested")
	assert_array(_call_required(panel, "get_adapter_event_names")).contains("boot_state_changed")
	assert_array(_call_required(dialog, "get_adapter_event_names")).contains("continue_requested")
	main_menu.queue_free()
	panel.queue_free()
	dialog.queue_free()

# acceptance: ACC:T192.9
func test_player_visible_continue_flow_updates_only_after_gate_acceptance() -> void:
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if dialog == null:
		return
	_call_required(dialog, "set_menu_state", ["main_menu"])
	assert_that(_call_required(dialog, "request_continue", [false])).is_equal(false)
	assert_that(_call_required(dialog, "get_menu_state")).is_equal("main_menu")
	assert_that(_call_required(dialog, "request_continue", [true])).is_equal(true)
	assert_that(_call_required(dialog, "get_menu_state")).is_equal("continue_requested")
	dialog.queue_free()

# acceptance: ACC:T192.10
func test_ui_wiring_uses_serializable_contract_payloads_without_godot_objects() -> void:
	var panel: Node = _instantiate_scene(BOOT_STATUS_PANEL_PATHS)
	var dialog: Node = _instantiate_scene(CONTINUE_GATE_DIALOG_PATHS)
	if panel == null or dialog == null:
		return
	var panel_payload: Variant = _call_required(panel, "to_contract_payload")
	var dialog_payload: Variant = _call_required(dialog, "to_contract_payload")
	assert_that(panel_payload is Dictionary).is_true()
	assert_that(dialog_payload is Dictionary).is_true()
	assert_that(panel_payload.values().any(func(value: Variant) -> bool: return value is Object)).is_false()
	assert_that(dialog_payload.values().any(func(value: Variant) -> bool: return value is Object)).is_false()
	panel.queue_free()
	dialog.queue_free()
