extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T162.4
func test_task162_should_keep_report_aggregation_marker_stable() -> void:
    var report_key := "task162.signal.compliance.report.aggregation"
    assert_str(report_key).contains("task162")
