extends AcceptDialog

const SURFACE_CONTRACT_KEY := "ContinueGateDialog"
const ADAPTER_EVENTS := ["continue_requested"]

var _menu_state := "main_menu"
var _gate_satisfied := false

@onready var _message_label: Label = $Margin/MessageLabel

func _ready() -> void:
	visible = true
	_refresh()

func evaluate_continue_gate(gate_satisfied: bool) -> bool:
	_gate_satisfied = gate_satisfied
	_refresh()
	return _gate_satisfied

func set_menu_state(state: String) -> void:
	_menu_state = state
	_refresh()

func get_menu_state() -> String:
	return _menu_state

func request_continue(gate_satisfied: bool) -> bool:
	if not evaluate_continue_gate(gate_satisfied):
		return false
	_menu_state = "continue_requested"
	_refresh()
	return true

func get_surface_contract_key() -> String:
	return SURFACE_CONTRACT_KEY

func get_adapter_event_names() -> Array:
	return ADAPTER_EVENTS.duplicate()

func to_contract_payload() -> Dictionary:
	return {
		"surface": SURFACE_CONTRACT_KEY,
		"menu_state": _menu_state,
		"gate_satisfied": _gate_satisfied,
	}

func _refresh() -> void:
	if is_instance_valid(_message_label):
		var gate_text := "ready" if _gate_satisfied else "blocked"
		_message_label.text = "Continue %s; menu state %s" % [gate_text, _menu_state]
