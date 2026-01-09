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

const _LOCALE_ZH := "zh"

var _bus: Node
var _created_bus := false

func before() -> void:
	_created_bus = false
	_bus = get_node_or_null("/root/EventBus")
	if _bus == null and ResourceLoader.exists("res://Game.Godot/Adapters/EventBusAdapter.cs"):
		_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
		_bus.name = "EventBus"
		get_tree().get_root().add_child(_bus)
		_created_bus = true

func after() -> void:
	if _created_bus and _bus != null and is_instance_valid(_bus):
		_bus.queue_free()
	_bus = null
	_created_bus = false

func _load_first_existing_packed_scene(paths: Array) -> PackedScene:
	for p in paths:
		if typeof(p) != TYPE_STRING:
			continue
		var path := String(p)
		if not ResourceLoader.exists(path):
			continue
		var res := load(path)
		if res is PackedScene:
			return res
	return null

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

func _find_first_text_node(root: Node) -> Node:
	if root is RichTextLabel:
		return root
	for child in root.get_children():
		if child is Node:
			var found := _find_first_text_node(child)
			if found != null:
				return found
	if root is Label:
		return root
	return null

func _read_text_from_node(node: Node) -> String:
	if node is Label:
		return String((node as Label).text)
	if node is RichTextLabel:
		return String((node as RichTextLabel).text)
	return ""

func _extract_visible_help_text(help_ui: Control) -> String:
	var cursor := help_ui
	while cursor != null:
		var text_node := _find_first_text_node(cursor)
		if text_node == null:
			return ""
		var canvas := text_node as CanvasItem
		if canvas != null and canvas.is_visible_in_tree():
			return _read_text_from_node(text_node)
		# If the first text node is not visible, try searching deeper by temporarily skipping it.
		# This keeps the function deterministic without relying on external assets.
		var parent := text_node.get_parent()
		if parent == null or not (parent is Node):
			return ""
		cursor = parent as Control
	return ""

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

func _try_navigate_once(help_ui: Control) -> bool:
	var next_btn := _find_first_button_by_keywords(help_ui, ["next", "forward"])
	if next_btn != null:
		next_btn.emit_signal("pressed")
		return true

	var tab_bar := _find_first_tab_bar(help_ui)
	if tab_bar != null and tab_bar.tab_count > 1:
		var next_tab := 1
		if tab_bar.current_tab == 1:
			next_tab = 0
		tab_bar.current_tab = next_tab
		if tab_bar.has_signal("tab_changed"):
			tab_bar.emit_signal("tab_changed", next_tab)
		return true

	var item_list := _find_first_item_list(help_ui)
	if item_list != null and item_list.item_count > 1:
		item_list.select(1)
		if item_list.has_signal("item_selected"):
			item_list.emit_signal("item_selected", 1)
		return true

	var option_button := _find_first_option_button(help_ui)
	if option_button != null and option_button.item_count > 1:
		option_button.select(1)
		if option_button.has_signal("item_selected"):
			option_button.emit_signal("item_selected", 1)
		return true

	return false

func _find_first_tab_bar(root: Node) -> TabBar:
	if root is TabBar:
		return root as TabBar
	for child in root.get_children():
		if child is Node:
			var found := _find_first_tab_bar(child)
			if found != null:
				return found
	return null

func _find_first_item_list(root: Node) -> ItemList:
	if root is ItemList:
		return root as ItemList
	for child in root.get_children():
		if child is Node:
			var found := _find_first_item_list(child)
			if found != null:
				return found
	return null

func _find_first_option_button(root: Node) -> OptionButton:
	if root is OptionButton:
		return root as OptionButton
	for child in root.get_children():
		if child is Node:
			var found := _find_first_option_button(child)
			if found != null:
				return found
	return null

func _instantiate_main_scene() -> Control:
	assert_bool(ResourceLoader.exists(MAIN_SCENE_PATH)).is_true()
	var packed := load(MAIN_SCENE_PATH)
	assert_bool(packed is PackedScene).is_true()
	var main := (packed as PackedScene).instantiate()
	add_child(auto_free(main))
	await get_tree().process_frame
	assert_bool(main.is_inside_tree()).is_true()
	assert_bool(main is Control).is_true()
	return main as Control

func _resolve_or_mount_help_ui(host: Control) -> Control:
	var help_packed := _load_first_existing_packed_scene(HELP_TUTORIAL_SCENE_CANDIDATES)
	if help_packed != null:
		var help_instance := help_packed.instantiate()
		add_child(auto_free(help_instance))
		await get_tree().process_frame
		assert_bool(help_instance is Control).is_true()
		return help_instance as Control

	# Try to reveal help UI from the main scene via a toggle method or a help button.
	var help_ui := _find_first_control_by_keywords(host, _HELP_KEYWORDS)
	if help_ui != null:
		return help_ui

	var toggled := _try_toggle_help(host)
	assert_bool(toggled).is_true()
	await get_tree().process_frame

	help_ui = _find_first_control_by_keywords(host, _HELP_KEYWORDS)
	assert_object(help_ui).is_not_null()
	return help_ui

# acceptance: ACC:T30.5
# Task 30: Help/Tutorial can toggle and navigate without pausing SceneTree.
func test_help_tutorial_toggle_and_navigation_does_not_pause_tree_and_shows_non_empty_step_text() -> void:
	assert_bool(get_tree().paused).is_false()

	if TranslationServer.has_method("set_locale"):
		TranslationServer.set_locale(_LOCALE_ZH)

	var main := await _instantiate_main_scene()
	var help_ui := await _resolve_or_mount_help_ui(main)
	assert_object(help_ui).is_not_null()
	if help_ui == null:
		return

	assert_bool(get_tree().paused).is_false()
	assert_bool(help_ui.is_inside_tree()).is_true()

	var canvas := help_ui as CanvasItem
	assert_object(canvas).is_not_null()

	var title_node := help_ui.get_node_or_null("Panel/VBox/SectionTitle")
	assert_object(title_node).is_not_null()
	assert_bool(title_node is Label).is_true()
	var title_label := title_node as Label
	var title_before := String(title_label.text)
	assert_bool(title_before.strip_edges().length() > 0).is_true()

	# Ensure the help UI is visible (toggled open).
	if not canvas.is_visible_in_tree():
		var toggled_on := _try_toggle_help(main)
		assert_bool(toggled_on).is_true()
		await get_tree().process_frame
		assert_bool(get_tree().paused).is_false()
	assert_bool(canvas.is_visible_in_tree()).is_true()

	var next_btn := _find_first_button_by_keywords(help_ui, ["next", "forward"])
	assert_object(next_btn).is_not_null()
	if next_btn == null:
		return

	var texts: Array[String] = []
	var content_node := help_ui.get_node_or_null("Panel/VBox/Content")
	assert_object(content_node).is_not_null()
	assert_bool(content_node is RichTextLabel).is_true()
	var content := content_node as RichTextLabel

	var current_text := String(content.text)
	assert_bool(current_text.strip_edges().length() > 0).is_true()
	texts.append(current_text)

	# Ensure steps are reachable sequentially (01 -> 06) via Next navigation.
	for _i in range(5):
		next_btn.emit_signal("pressed")
		await get_tree().process_frame
		assert_bool(get_tree().paused).is_false()
		assert_str(String(title_label.text)).is_equal(title_before)
		var t := String(content.text)
		assert_bool(t.strip_edges().length() > 0).is_true()
		assert_bool(t != current_text).is_true()
		current_text = t
		texts.append(t)

	var uniq := {}
	for t in texts:
		uniq[String(t)] = true
	assert_int(uniq.size()).is_equal(texts.size())

	# After the 01 -> 06 learning route steps, navigating further should reach the knowledge base section.
	next_btn.emit_signal("pressed")
	await get_tree().process_frame
	var title_after := String(title_label.text)
	assert_bool(title_after.strip_edges().length() > 0).is_true()
	assert_bool(title_after != title_before).is_true()

	# Close the help UI (toggled close).
	var toggled_off := _try_toggle_help(main)
	assert_bool(toggled_off).is_true()
	await get_tree().process_frame
	assert_bool(get_tree().paused).is_false()
	assert_bool(canvas.is_visible_in_tree()).is_false()
