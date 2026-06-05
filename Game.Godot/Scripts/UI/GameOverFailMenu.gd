extends Control

const SURFACE_CONTRACT_KEY := "GameOverFailMenu"
const ADAPTER_EVENTS := ["main_menu_requested"]

var _route_requested := false

@onready var _message_label: Label = $Center/Panel/Margin/VBox/MessageLabel

func _ready() -> void:
	visible = true
	_refresh()

func request_main_menu() -> bool:
	_route_requested = true
	_refresh()
	return true

func get_route_requested() -> bool:
	return _route_requested

func get_surface_contract_key() -> String:
	return SURFACE_CONTRACT_KEY

func get_adapter_event_names() -> Array:
	return ADAPTER_EVENTS.duplicate()

func to_contract_payload() -> Dictionary:
	return {
		"surface": SURFACE_CONTRACT_KEY,
		"route_requested": _route_requested,
	}

func _on_main_menu_button_pressed() -> void:
	request_main_menu()

func _refresh() -> void:
	if is_instance_valid(_message_label):
		var route_text := "Main menu route requested" if _route_requested else "Return to main menu"
		_message_label.text = "Game over failure. %s." % route_text
