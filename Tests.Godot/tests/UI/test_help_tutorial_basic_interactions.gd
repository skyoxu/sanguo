extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const MAIN_MENU_SCENE_PATH := "res://Game.Godot/Scenes/UI/MainMenu.tscn"
const HELP_TUTORIAL_SCENE_PATH := "res://Game.Godot/Scenes/UI/HelpTutorial.tscn"
const HELP_TUTORIAL_ROOT_NODE_NAME := "HelpTutorial"
const HELP_TUTORIAL_GROUP_NAME := "help_tutorial"

func after() -> void:
	var nodes := get_tree().get_nodes_in_group(HELP_TUTORIAL_GROUP_NAME)
	for n in nodes:
		if n != null and is_instance_valid(n):
			n.queue_free()
	await get_tree().process_frame

# acceptance: ACC:T30.2
# Task 30: Help/Tutorial basic interactions must be observable in headless tests.
func test_help_tutorial_can_open_from_main_menu_and_navigate_steps_and_close() -> void:
	assert_bool(ResourceLoader.exists(MAIN_MENU_SCENE_PATH)).is_true()
	assert_bool(ResourceLoader.exists(HELP_TUTORIAL_SCENE_PATH)).is_true()

	var menu_packed := load(MAIN_MENU_SCENE_PATH)
	assert_bool(menu_packed is PackedScene).is_true()
	var menu := (menu_packed as PackedScene).instantiate()
	add_child(auto_free(menu))
	await get_tree().process_frame

	var help_btn := menu.get_node_or_null("VBox/BtnHelp")
	assert_object(help_btn).is_not_null()
	assert_bool(help_btn is Button).is_true()

	(help_btn as Button).emit_signal("pressed")
	await get_tree().process_frame

	var help_ui := get_tree().get_root().get_node_or_null(HELP_TUTORIAL_ROOT_NODE_NAME)
	assert_object(help_ui).is_not_null()
	assert_bool(help_ui is Control).is_true()

	var help_control := help_ui as Control
	assert_bool(help_control.is_inside_tree()).is_true()
	assert_bool(help_control.visible).is_true()

	var content := help_control.get_node_or_null("Panel/VBox/Content")
	assert_object(content).is_not_null()
	assert_bool(content is RichTextLabel).is_true()
	var text_before := String((content as RichTextLabel).text)
	assert_bool(text_before.strip_edges().length() > 0).is_true()

	var btn_next := help_control.get_node_or_null("Panel/VBox/HBox/BtnNext")
	assert_object(btn_next).is_not_null()
	assert_bool(btn_next is Button).is_true()
	(btn_next as Button).emit_signal("pressed")
	await get_tree().process_frame

	var text_after := String((content as RichTextLabel).text)
	assert_bool(text_after.strip_edges().length() > 0).is_true()
	assert_bool(text_after != text_before).is_true()

	var btn_close := help_control.get_node_or_null("Panel/VBox/HBox/BtnClose")
	assert_object(btn_close).is_not_null()
	assert_bool(btn_close is Button).is_true()
	(btn_close as Button).emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(help_control.visible).is_false()
