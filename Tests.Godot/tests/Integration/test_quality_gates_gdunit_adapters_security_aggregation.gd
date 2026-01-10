extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const ADAPTERS_TESTS_DIR := "res://tests/Adapters"
const SECURITY_TESTS_DIR := "res://tests/Security"

func _select_gate_suite_dirs() -> PackedStringArray:
	return PackedStringArray([ADAPTERS_TESTS_DIR, SECURITY_TESTS_DIR])

func _aggregate_all_passed(passed_flags: Array[bool]) -> bool:
	for passed in passed_flags:
		if not passed:
			return false
	return true

# acceptance: ACC:T47.3
func test_gate_suite_selection_is_deterministic_and_stable() -> void:
	var suite_dirs := _select_gate_suite_dirs()
	assert_int(suite_dirs.size()).is_equal(2)
	assert_str(suite_dirs[0]).is_equal(ADAPTERS_TESTS_DIR)
	assert_str(suite_dirs[1]).is_equal(SECURITY_TESTS_DIR)

# acceptance: ACC:T47.3
func test_aggregation_is_failed_when_any_suite_failed() -> void:
	assert_bool(_aggregate_all_passed([true, true])).is_true()
	assert_bool(_aggregate_all_passed([true, false])).is_false()
	assert_bool(_aggregate_all_passed([false, true])).is_false()
	assert_bool(_aggregate_all_passed([false, false])).is_false()
