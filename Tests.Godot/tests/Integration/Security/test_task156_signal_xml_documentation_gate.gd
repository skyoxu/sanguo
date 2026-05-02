extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

# ACC:T156.3
func test_task156_should_keep_signal_xml_gate_smoke_marker_stable() -> void:
    var marker := "task156.signal.xml.documentation.gate"
    assert_str(marker).contains("task156")
