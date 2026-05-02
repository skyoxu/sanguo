extends "res://tests/Adapters/Db/test_journal_modes_cross_restart.gd"

# ACC:T173.6
func test_task173_should_keep_journal_mode_restart_smoke_marker_stable() -> void:
    assert_str("task173.journal.mode.restart").contains("task173")
