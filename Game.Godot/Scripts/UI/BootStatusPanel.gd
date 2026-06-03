extends PanelContainer

const SURFACE_CONTRACT_KEY := "BootStatusPanel"
const ADAPTER_EVENTS := ["boot_state_changed"]

var _boot_state := "initializing"
var _message := "Boot status initializing"

@onready var _status_label: Label = $Margin/StatusLabel

func _ready() -> void:
	visible = true
	_refresh()

func set_boot_state(state: String, message: String) -> void:
	_boot_state = state
	_message = message
	_refresh()

func get_status_text() -> String:
	return _status_label.text if is_instance_valid(_status_label) else _format_status()

func get_surface_contract_key() -> String:
	return SURFACE_CONTRACT_KEY

func get_adapter_event_names() -> Array:
	return ADAPTER_EVENTS.duplicate()

func to_contract_payload() -> Dictionary:
	return {
		"surface": SURFACE_CONTRACT_KEY,
		"boot_state": _boot_state,
		"message": _message,
		"status_text": _format_status(),
	}

func _refresh() -> void:
	if is_instance_valid(_status_label):
		_status_label.text = _format_status()

func _format_status() -> String:
	return "%s: %s" % [_boot_state, _message]
