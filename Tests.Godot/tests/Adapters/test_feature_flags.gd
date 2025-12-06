extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _remove_flags_file() -> void:
    var rel := "user://config/features.json"
    var abs := ProjectSettings.globalize_path(rel)
    if FileAccess.file_exists(rel):
        DirAccess.remove_absolute(abs)

func before() -> void:
    _remove_flags_file()
    var flags = preload("res://Game.Godot/Scripts/Config/FeatureFlags.cs").new()
    flags.name = "FeatureFlags"
    get_tree().get_root().add_child(auto_free(flags))

func test_enable_disable_and_is_enabled() -> void:
    var ff = get_node("/root/FeatureFlags")
    assert_object(ff).is_not_null()
    # default should be false (no env override, no file)
    assert_bool(ff.IsEnabled("demo_screens")).is_false()
    # enable then verify
    ff.Enable("demo_screens")
    await get_tree().process_frame
    assert_bool(ff.IsEnabled("demo_screens")).is_true()
    # disable then verify
    ff.Disable("demo_screens")
    await get_tree().process_frame
    assert_bool(ff.IsEnabled("demo_screens")).is_false()


