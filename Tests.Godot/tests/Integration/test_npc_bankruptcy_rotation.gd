extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const ROTATION_ADAPTER_SCRIPT := "res://Game.Godot/Adapters/NpcBankruptcyRotationAdapter.gd"
const PLAYER_ID := "player"
const NPC_ID := "npc_001"

func _create_rotation_adapter() -> Node:
	var script := load(ROTATION_ADAPTER_SCRIPT)
	assert_that(script).is_not_null()
	var adapter := script.new()
	assert_that(adapter).is_not_null()
	return adapter

# acceptance: ACC:T197.12
# The minimal NPC bankruptcy adapter must wire game over state into turn rotation.
func test_npc_bankruptcy_wires_gameover_before_next_turn() -> void:
	var adapter := _create_rotation_adapter()
	add_child(adapter)

	assert_that(adapter.has_method("seed_turn_order")).is_true()
	assert_that(adapter.has_method("mark_bankrupt")).is_true()
	assert_that(adapter.has_method("advance_turn_async")).is_true()
	assert_that(adapter.has_method("is_game_over")).is_true()
	assert_that(adapter.has_method("current_actor_id")).is_true()

	adapter.seed_turn_order([PLAYER_ID, NPC_ID])
	adapter.mark_bankrupt(NPC_ID)
	await adapter.advance_turn_async()

	assert_that(adapter.is_game_over()).is_true()
	assert_that(adapter.current_actor_id()).is_equal(PLAYER_ID)

# acceptance: ACC:T197.13
# Advancing after game over must be refused and must not rotate away from the player.
func test_advance_turn_after_npc_bankruptcy_gameover_is_refused_without_rotation() -> void:
	var adapter := _create_rotation_adapter()
	add_child(adapter)

	assert_that(adapter.has_method("seed_turn_order")).is_true()
	assert_that(adapter.has_method("mark_bankrupt")).is_true()
	assert_that(adapter.has_method("advance_turn_async")).is_true()
	assert_that(adapter.has_method("last_error_name")).is_true()
	assert_that(adapter.has_method("current_actor_id")).is_true()

	adapter.seed_turn_order([PLAYER_ID, NPC_ID])
	adapter.mark_bankrupt(NPC_ID)
	await adapter.advance_turn_async()
	var actor_after_gameover := adapter.current_actor_id()

	await adapter.advance_turn_async()

	assert_that(adapter.current_actor_id()).is_equal(actor_after_gameover)
	assert_that(adapter.last_error_name()).is_equal("InvalidOperationException")
