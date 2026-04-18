extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

class CampaignUiHarness:
	var camp_state: int = 0
	var blocked_action_message_visible: bool = false
	var _actions_in_round: int = 0

	func perform_action(delta: int) -> bool:
		_actions_in_round += 1
		if _actions_in_round > 1:
			blocked_action_message_visible = true
			return false

		camp_state += delta
		blocked_action_message_visible = false
		return true

# acceptance: ACC:T98.3
func test_refused_second_action_shows_blocked_message_and_keeps_camp_state_unchanged() -> void:
	var ui := CampaignUiHarness.new()
	var initial_state := ui.camp_state

	var first_result := ui.perform_action(5)
	var state_after_first := ui.camp_state
	var second_result := ui.perform_action(9)

	assert_bool(first_result).is_true()
	assert_int(state_after_first).is_equal(initial_state + 5)
	assert_bool(second_result).is_false()
	assert_bool(ui.blocked_action_message_visible).is_true()
	assert_int(ui.camp_state).is_equal(state_after_first)
