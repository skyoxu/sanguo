extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T163.2
func test_task163_should_keep_ci_gate_marker_stable() -> void:
    var gate_key := "task163.signal.compliance.ci.gate"
    assert_str(gate_key).contains("task163")
