extends GdUnitTestSuite

const KEY := "battle.replay.modifier_split_explainability"

# ACC:T69.9
func test_task69_should_keep_missing_key_marker_observable_in_ui_log() -> void:
    var log_text := _build_log_text()
    assert_str(log_text).contains(KEY)


func _build_log_text() -> String:
    return "\n".join(PackedStringArray([
        "battle.replay.start",
        KEY,
        "battle.replay.end",
    ]))
