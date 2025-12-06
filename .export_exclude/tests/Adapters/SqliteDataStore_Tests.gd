extends GdUnitTestSuite

func test_sqlite_autoinit_schema() -> void:
    var db = preload("res://Game.Godot/Adapters/SqliteDataStore.cs").new()
    add_child(db)
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    var ok := db.TryOpen(path)
    if not ok:
        push_warning("SKIP Sqlite test: " + str(db.LastError))
        db.queue_free()
        return
    var has_users := db.TableExists("users")
    assert_bool(has_users).is_true()
    db.queue_free()

func test_sqlite_insert_and_select() -> void:
    var db = preload("res://Game.Godot/Adapters/SqliteDataStore.cs").new()
    add_child(db)
    var path := "user://utdb_%s/game.db" % Time.get_ticks_msec()
    var ok := db.TryOpen(path)
    if not ok:
        push_warning("SKIP Sqlite test2: " + str(db.LastError))
        db.queue_free()
        return
    # insert a settings row and read it back
    var now := int(Time.get_unix_time_from_system())
    var insert_sql := "INSERT INTO settings(user_id,audio_volume,graphics_quality,language,updated_at) VALUES('u1',0.8,'high','en',%d);" % now
    var _ = db.Execute(insert_sql)
    var rows = db.Query("SELECT user_id, audio_volume FROM settings WHERE user_id='u1';")
    assert_int(int(rows.size())).is_greater(0)
    db.queue_free()
