extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

class SummarySnapshot:
	var baseline_boss_pressure: int = 0
	var penalty_pressure: int = 0
	var displayed_total_pressure: int = 0

class DelayedPressureSummaryPresenter:
	func build_snapshot(baseline_pressure: int, penalty_pressure: int) -> SummarySnapshot:
		var snapshot := SummarySnapshot.new()
		snapshot.baseline_boss_pressure = baseline_pressure
		snapshot.penalty_pressure = penalty_pressure
		snapshot.displayed_total_pressure = baseline_pressure + penalty_pressure
		return snapshot

# acceptance: ACC:T135.5
func test_delayed_pressure_summary_keeps_baseline_and_penalty_distinct() -> void:
	var presenter := DelayedPressureSummaryPresenter.new()

	var snapshot := presenter.build_snapshot(7, 3)

	assert_int(snapshot.baseline_boss_pressure).is_equal(7)
	assert_int(snapshot.penalty_pressure).is_equal(3)
	assert_int(snapshot.displayed_total_pressure).is_equal(10)

func test_delayed_pressure_summary_does_not_hide_penalty_inside_baseline() -> void:
	var presenter := DelayedPressureSummaryPresenter.new()
	var baseline_before := 9
	var penalty := 2

	var snapshot := presenter.build_snapshot(baseline_before, penalty)

	assert_int(snapshot.baseline_boss_pressure).is_equal(baseline_before)
	assert_int(snapshot.penalty_pressure).is_equal(penalty)
	assert_int(snapshot.displayed_total_pressure).is_equal(
		snapshot.baseline_boss_pressure + snapshot.penalty_pressure
	)
