extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_persistence_cross_restart() -> void:
    var cfg_path = "user://settings_%s.cfg" % Time.get_unix_time_from_system()
    var cfg = ConfigFile.new()
    cfg.set_value("app", "volume", 0.7)
    cfg.set_value("app", "lang", "en")
    var err = cfg.save(cfg_path)
    assert_int(err).is_equal(0)

    await get_tree().process_frame

    var cfg2 = ConfigFile.new()
    var err2 = cfg2.load(cfg_path)
    assert_int(err2).is_equal(0)
    assert_float(float(cfg2.get_value("app", "volume", 0.0))).is_equal(0.7)
    assert_str(str(cfg2.get_value("app", "lang", ""))).is_equal("en")

