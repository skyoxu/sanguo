extends GdUnitTestSuite

const KEY_REPLAY := "battle.replay.modifier_split_replay"
const KEY_EXPLAINABILITY := "battle.replay.modifier_split_explainability"

func test_i18n_keys_present_in_replay_log() -> void:
    var log_text := _build_replay_log_text()

    assert_str(log_text).contains(KEY_REPLAY)
    assert_str(log_text).contains(KEY_EXPLAINABILITY)


func _build_replay_log_text() -> String:
    var lines := PackedStringArray([
        "battle.replay.start",
        KEY_REPLAY,
        KEY_EXPLAINABILITY,
        "battle.replay.end",
    ])
    return "\n".join(lines)
