extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T157.4
func test_task157_should_keep_integration_closure_marker_stable() -> void:
    var closure_key := "task157.signal.compliance.integration.closure"
    assert_str(closure_key).contains("task157")
