extends Node

var _turn_order: Array[String] = []
var _current_index := 0
var _bankrupt_ids := {}
var _game_over := false
var _last_error_name := ""

func seed_turn_order(player_ids: Array) -> void:
	_turn_order.clear()
	for player_id in player_ids:
		var value := str(player_id)
		if not value.is_empty():
			_turn_order.append(value)
	_current_index = 0
	_bankrupt_ids.clear()
	_game_over = false
	_last_error_name = ""

func mark_bankrupt(player_id: String) -> void:
	if player_id.is_empty():
		return
	_bankrupt_ids[player_id] = true
	_remove_bankrupt_npcs()
	if _turn_order.size() <= 1:
		_game_over = true

func advance_turn_async() -> void:
	if _game_over:
		_last_error_name = "InvalidOperationException"
		return

	_remove_bankrupt_npcs()
	if _turn_order.size() <= 1:
		_game_over = true
		return

	_current_index = (_current_index + 1) % _turn_order.size()

func is_game_over() -> bool:
	return _game_over

func current_actor_id() -> String:
	if _turn_order.is_empty():
		return ""
	return _turn_order[_current_index]

func last_error_name() -> String:
	return _last_error_name

func _remove_bankrupt_npcs() -> void:
	if _turn_order.is_empty():
		return

	var current_actor := current_actor_id()
	var kept: Array[String] = []
	for player_id in _turn_order:
		if _bankrupt_ids.has(player_id) and _is_npc_id(player_id):
			continue
		kept.append(player_id)

	_turn_order = kept
	if _turn_order.is_empty():
		_current_index = 0
		return

	var current_kept_index := _turn_order.find(current_actor)
	_current_index = current_kept_index if current_kept_index >= 0 else 0

func _is_npc_id(player_id: String) -> bool:
	return player_id.begins_with("npc") or player_id.begins_with("ai-")
