extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_SCENE_PATH := "res://Game.Godot/Scenes/UI/MainMenu.tscn"

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

func _find_node_by_keywords(root: Node, keywords: Array) -> Node:
	var node_name := String(root.name).to_lower()
	for k in keywords:
		if typeof(k) != TYPE_STRING:
			continue
		var needle := String(k).to_lower()
		if node_name.find(needle) >= 0:
			return root
	for child in root.get_children():
		if child is Node:
			var found := _find_node_by_keywords(child, keywords)
			if found != null:
				return found
	return null

func test_suite_can_mount_a_control_in_tree() -> void:
	var control := Control.new()
	add_child(auto_free(control))
	await get_tree().process_frame
	assert_bool(control.is_inside_tree()).is_true()

# acceptance: ACC:T30.1
# Task 30: Help/Tutorial entry can be instantiated headless.
func test_help_or_tutorial_ui_can_instantiate_headless() -> void:
	var packed := _load_first_existing_packed_scene(HELP_TUTORIAL_SCENE_CANDIDATES)
	if packed != null:
		var instance := packed.instantiate()
		assert_object(instance).is_not_null()
		if instance == null:
			return
		add_child(auto_free(instance))
		await get_tree().process_frame
		assert_bool(instance.is_inside_tree()).is_true()
		assert_bool(instance is Control).is_true()

		var canvas := instance as CanvasItem
		if canvas != null:
			canvas.hide()
			await get_tree().process_frame
			assert_bool(canvas.visible).is_false()
			canvas.show()
			await get_tree().process_frame
			assert_bool(canvas.visible).is_true()
		return

	var main_menu_packed := _load_first_existing_packed_scene([MAIN_MENU_SCENE_PATH])
	assert_object(main_menu_packed).is_not_null()
	if main_menu_packed == null:
		return
	var main_menu := main_menu_packed.instantiate()
	assert_object(main_menu).is_not_null()
	if main_menu == null:
		return
	add_child(auto_free(main_menu))
	await get_tree().process_frame
	assert_bool(main_menu.is_inside_tree()).is_true()

	var help_node := _find_node_by_keywords(main_menu, ["help", "tutorial"])
	assert_object(help_node).is_not_null()
	if help_node == null:
		return
	assert_bool(help_node is Control).is_true()
	assert_bool(help_node.is_inside_tree()).is_true()
