extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"
const FreezeFeedbackGuard = preload("res://scripts/security/freeze_feedback_guard.gd")

# acceptance: ACC:T154.1
func test_non_crash_diagnostics_are_suppressed_from_user_facing_feedback() -> void:
	var guard := FreezeFeedbackGuard.new()
	var result := guard.evaluate("non_crash_diagnostic")

	assert_that(result.get("feedback", false)).is_false()
	assert_that(result.get("audit_only", false)).is_true()

# acceptance: ACC:T154.2
func test_crash_category_can_trigger_user_facing_feedback() -> void:
	var guard := FreezeFeedbackGuard.new()
	var result := guard.evaluate("crash")

	assert_that(result.get("feedback", false)).is_true()

# acceptance: ACC:T154.3
func test_non_crash_path_keeps_audit_marker() -> void:
	var guard := FreezeFeedbackGuard.new()
	var result := guard.evaluate("non_crash_diagnostic")

	assert_that(result.get("category", "")).is_equal("non_crash_diagnostic")
	assert_that(result.get("audit_only", false)).is_true()
