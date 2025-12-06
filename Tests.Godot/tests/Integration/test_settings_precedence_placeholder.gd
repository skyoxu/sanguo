extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func _new_db() -> Node:
	var db = null
	if ClassDB.class_exists("SqliteDataStore"):
		db = ClassDB.instantiate("SqliteDataStore")
	else:
		var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
		if s == null or not s.has_method("new"):
			push_warning("SKIP: CSharpScript.new() unavailable, skip DB new")
			return null
		db = s.new()
	db.name = "SqlDb"
	get_tree().get_root().add_child(auto_free(db))
	await get_tree().process_frame
	return db

func _force_managed() -> void:
	var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
	add_child(auto_free(helper))
	helper.ForceManaged()

func _write_config(path: String, lang: String) -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("settings", "lang", lang)
	var err := cfg.save(path)
	assert_int(err).is_equal(Error.OK)

func test_settings_configfile_wins_over_db() -> void:
	# Prepare conflicting sources: ConfigFile(lang="zh") vs DB(lang="en"); ConfigFile must win (ADR-0023)
	var cfg_path := "user://settings.cfg"
	_write_config(cfg_path, "zh")
	_force_managed()
	var db = await _new_db()
	if db == null:
		push_warning("SKIP: missing C# instantiate, skip test")
		return
	var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
	add_child(auto_free(helper))
	var ok = db.TryOpen("user://utdb_%s/settings_pref.db" % Time.get_unix_time_from_system())
	assert_bool(ok).is_true()
	helper.ExecSql("CREATE TABLE IF NOT EXISTS settings(user_id TEXT PRIMARY KEY, audio_volume REAL, graphics_quality TEXT, language TEXT, updated_at INTEGER);")
	helper.ExecSql("INSERT OR REPLACE INTO settings(user_id,audio_volume,graphics_quality,language,updated_at) VALUES('default',0.5,'medium','en',%d);" % Time.get_unix_time_from_system())

	var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
	if packed == null:
		push_warning("SKIP: SettingsPanel.tscn not found")
		return
	var panel = packed.instantiate()
	add_child(auto_free(panel))
	await get_tree().process_frame
	var load_btn = panel.get_node("VBox/Buttons/LoadBtn")
	load_btn.emit_signal("pressed")
	await get_tree().process_frame

	var effective := TranslationServer.get_locale()
	assert_str(effective).contains("zh")
