extends RefCounted

const _MENU_PATHS: Array[String] = [
	"MenuLayer/MainMenu",
	"MainMenu",
]

const _BTN_PLAY_PATHS: Array[String] = [
	"MenuRow/MenuBox/BtnPlay",
	"VBox/BtnPlay",
]

const _BTN_LOAD_PATHS: Array[String] = [
	"MenuRow/MenuBox/BtnLoad",
	"VBox/BtnLoad",
]

const _BTN_START_PATHS: Array[String] = [
	"ConfigCenter/NewGameConfig/Margin/Root/BottomBar/BottomButtons/BtnStart",
	"ConfigCenter/NewGameConfig/VBox/BtnStart",
]

const _BTN_QUIT_PATHS: Array[String] = [
	"MenuRow/MenuBox/BtnQuit",
	"VBox/BtnQuit",
]

static func resolve_menu(root: Node) -> Node:
	if root == null:
		return null
	if root.name == "MainMenu":
		return root
	for path in _MENU_PATHS:
		var node = root.get_node_or_null(path)
		if node != null:
			return node
	return null

static func resolve_play_button(menu: Node) -> Button:
	return _resolve_button(menu, _BTN_PLAY_PATHS)

static func resolve_load_button(menu: Node) -> Button:
	return _resolve_button(menu, _BTN_LOAD_PATHS)

static func resolve_start_button(menu: Node) -> Button:
	return _resolve_button(menu, _BTN_START_PATHS)

static func resolve_status_label(menu: Node) -> Label:
	if menu == null:
		return null
	var node = menu.get_node_or_null("StatusLabel")
	if node is Label:
		return node
	return null

static func resolve_load_panel(menu: Node) -> Control:
	if menu == null:
		return null
	var node = menu.get_node_or_null("LoadPanel")
	if node is Control:
		return node
	return null

static func resolve_quit_button(menu: Node) -> Button:
	return _resolve_button(menu, _BTN_QUIT_PATHS)

static func press_play_then_start(menu: Node) -> bool:
	var play = resolve_play_button(menu)
	if play == null:
		return false
	play.emit_signal("pressed")

	var start = resolve_start_button(menu)
	if start == null:
		return false
	start.emit_signal("pressed")
	return true

static func _resolve_button(root: Node, paths: Array[String]) -> Button:
	if root == null:
		return null
	for path in paths:
		var node = root.get_node_or_null(path)
		if node is Button:
			return node
	return null
