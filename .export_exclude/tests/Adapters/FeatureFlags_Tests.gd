extends GdUnitTestSuite

const CFG_DIR := "user://config"
const CFG_PATH := CFG_DIR + "/features.json"

func _clear_config() -> void:
    if FileAccess.file_exists(CFG_PATH):
        DirAccess.remove_absolute(ProjectSettings.globalize_path(CFG_PATH))

func _write_config(json: String) -> void:
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CFG_DIR))
    var f := FileAccess.open(CFG_PATH, FileAccess.WRITE)
    f.store_string(json)
    f.flush()
    f.close()

func test_featureflags_reads_from_file() -> void:
    _clear_config()
    _write_config('{"demo_screens": true}')
    var ff = preload("res://Game.Godot/Scripts/Config/FeatureFlags.cs").new()
    add_child(ff)
    assert_bool(ff.IsEnabled("demo_screens")).is_true()
    ff.queue_free()

func test_featureflags_defaults_to_false() -> void:
    _clear_config()
    var ff = preload("res://Game.Godot/Scripts/Config/FeatureFlags.cs").new()
    add_child(ff)
    assert_bool(ff.IsEnabled("unknown_flag")).is_false()
    ff.queue_free()

func test_featureflags_save_and_reload() -> void:
    _clear_config()
    var ff = preload("res://Game.Godot/Scripts/Config/FeatureFlags.cs").new()
    add_child(ff)
    ff.Enable("perf_overlay")
    ff.Save()
    ff.queue_free()
    # Reload to verify persisted state
    var ff2 = preload("res://Game.Godot/Scripts/Config/FeatureFlags.cs").new()
    add_child(ff2)
    assert_bool(ff2.IsEnabled("perf_overlay")).is_true()
    ff2.queue_free()
    _clear_config()

