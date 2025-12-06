extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_configfile_utf8_roundtrip() -> void:
    var path = "user://settings_%s.cfg" % Time.get_unix_time_from_system()
    var cfg := ConfigFile.new()
    var note := "你好，世界！äöü✓"
    cfg.set_value("app", "volume", 0.66)
    cfg.set_value("app", "lang", "zh")
    cfg.set_value("app", "note", note)
    var err = cfg.save(path)
    assert_int(err).is_equal(0)
    await get_tree().process_frame

    var cfg2 := ConfigFile.new()
    var err2 = cfg2.load(path)
    assert_int(err2).is_equal(0)
    assert_float(float(cfg2.get_value("app", "volume", 0.0))).is_equal(0.66)
    assert_str(str(cfg2.get_value("app", "lang", ""))).is_equal("zh")
    assert_str(str(cfg2.get_value("app", "note", ""))).is_equal(note)

