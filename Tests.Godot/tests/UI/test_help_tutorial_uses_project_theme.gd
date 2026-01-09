extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_SCENE_PATH := "res://Game.Godot/Scenes/Main.tscn"

const HELP_TUTORIAL_SCENE_CANDIDATES := [
	"res://Game.Godot/Scenes/UI/HelpTutorial.tscn",
	"res://Game.Godot/Scenes/UI/HelpPanel.tscn",
	"res://Game.Godot/Scenes/UI/HelpOverlay.tscn",
	"res://Game.Godot/Scenes/UI/Help.tscn",
	"res://Game.Godot/Scenes/Sanguo/SanguoHelp.tscn",
	"res://Game.Godot/Scenes/Sanguo/HelpTutorial.tscn",
	"res://Game.Godot/Scenes/Sanguo/Help.tscn",
	"res://Game.Godot/Scenes/Sanguo/Tutorial.tscn",
	"res://Game.Godot/Scenes/UI/Tutorial.tscn",
]

const _HELP_KEYWORDS := ["help", "tutorial"]

const _HELP_TOGGLE_METHODS := [
	"ToggleHelpTutorial",
	"ToggleHelpOverlay",
	"ToggleHelp",
	"ToggleTutorial",
	"OpenHelpTutorial",
	"OpenHelp",
	"ShowHelpTutorial",
	"ShowHelp",
]

func _load_packed_scene_or_null(path: String) -> PackedScene:
	if path.is_empty() or not ResourceLoader.exists(path):
		return null
	var res := load(path)
	if res is PackedScene:
		return res
	return null

func _instantiate_main_scene() -> Control:
	assert_bool(ResourceLoader.exists(MAIN_SCENE_PATH)).is_true()
	var packed := _load_packed_scene_or_null(MAIN_SCENE_PATH)
	assert_object(packed).is_not_null()
	var main := (packed as PackedScene).instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	assert_bool(main is Control).is_true()
	assert_bool(main.is_inside_tree()).is_true()
	return main as Control

func _find_first_button_by_keywords(root: Node, keywords: Array) -> Button:
	if root is Button:
		var node_name := String(root.name).to_lower()
		for k in keywords:
			if typeof(k) != TYPE_STRING:
				continue
			var needle := String(k).to_lower()
			if node_name.find(needle) >= 0:
				return root as Button
	for child in root.get_children():
		if child is Node:
			var found := _find_first_button_by_keywords(child, keywords)
			if found != null:
				return found
	return null

func _find_first_control_by_keywords(root: Node, keywords: Array) -> Control:
	if root is Control:
		var node_name := String(root.name).to_lower()
		for k in keywords:
			if typeof(k) != TYPE_STRING:
				continue
			var needle := String(k).to_lower()
			if node_name.find(needle) >= 0:
				return root as Control
	for child in root.get_children():
		if child is Node:
			var found := _find_first_control_by_keywords(child, keywords)
			if found != null:
				return found
	return null

func _try_toggle_help(host: Node) -> bool:
	var candidates: Array[Node] = []
	candidates.append(host)
	var hud := host.get_node_or_null("HUD")
	if hud != null:
		candidates.append(hud)
	var main_menu := host.get_node_or_null("MainMenu")
	if main_menu != null:
		candidates.append(main_menu)

	for node in candidates:
		for method_name in _HELP_TOGGLE_METHODS:
			if node != null and node.has_method(String(method_name)):
				node.call(String(method_name))
				return true

	var help_btn := _find_first_button_by_keywords(host, _HELP_KEYWORDS)
	if help_btn != null:
		help_btn.emit_signal("pressed")
		return true

	return false

func _resolve_or_mount_help_ui(host: Control) -> Control:
	for p in HELP_TUTORIAL_SCENE_CANDIDATES:
		if typeof(p) != TYPE_STRING:
			continue
		var path := String(p)
		var packed := _load_packed_scene_or_null(path)
		if packed == null:
			continue
		var instance := (packed as PackedScene).instantiate()
		add_child(auto_free(instance))
		await get_tree().process_frame
		if instance is Control:
			return instance as Control

	var help_ui := _find_first_control_by_keywords(host, _HELP_KEYWORDS)
	if help_ui != null:
		return help_ui

	if _try_toggle_help(host):
		await get_tree().process_frame
		help_ui = _find_first_control_by_keywords(host, _HELP_KEYWORDS)
		if help_ui != null:
			return help_ui

	return null

func _effective_theme(control: Control) -> Theme:
	if control == null:
		return null
	if control.has_method("get_theme"):
		return control.get_theme()
	return control.theme

# acceptance: ACC:T30.3
# Task 30: Help/Tutorial UI should reuse the project Theme.
func test_help_tutorial_uses_project_theme_or_inherits_from_main() -> void:
	var main := await _instantiate_main_scene()
	var main_theme := _effective_theme(main)
	assert_object(main_theme).is_not_null()
	if main_theme == null:
		return

	var main_theme_path := String(main_theme.resource_path)
	if not main_theme_path.is_empty():
		assert_bool(ResourceLoader.exists(main_theme_path)).is_true()

	var help_ui := await _resolve_or_mount_help_ui(main)
	assert_object(help_ui).is_not_null()
	if help_ui == null:
		return

	var help_theme := _effective_theme(help_ui)
	assert_object(help_theme).is_not_null()
	if help_theme == null:
		return

	var help_theme_path := String(help_theme.resource_path)
	if not main_theme_path.is_empty() and not help_theme_path.is_empty():
		assert_str(help_theme_path).is_equal(main_theme_path)
	else:
		assert_bool(help_theme == main_theme).is_true()
