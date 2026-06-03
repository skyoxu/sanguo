extends Control

const SURFACE_CONTRACT_KEY := "MainMenu"
const ENTRY_STATE := "boot_menu_entry"
const ADAPTER_EVENTS := ["menu_entry_requested"]

func _ready() -> void:
	visible = true

func get_entry_state() -> String:
	return ENTRY_STATE

func get_surface_contract_key() -> String:
	return SURFACE_CONTRACT_KEY

func get_adapter_event_names() -> Array:
	return ADAPTER_EVENTS.duplicate()
