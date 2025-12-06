extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_configfile_path_security() -> void:
    var safe := preload("res://Game.Godot/Adapters/Security/SafeConfig.gd").new()
    add_child(auto_free(safe))
    var sections := { "s": { "k": "v" } }
    # allow: user://
    var ok = safe.save_user("user://ok_settings.cfg", sections)
    assert_int(ok).is_equal(0)

    # deny: absolute path
    var abs = safe.save_user("C:/temp/bad_settings.cfg", sections)
    assert_bool(abs != 0).is_true()

    # deny: traversal
    var trav = safe.save_user("user://../bad_settings.cfg", sections)
    assert_bool(trav != 0).is_true()
