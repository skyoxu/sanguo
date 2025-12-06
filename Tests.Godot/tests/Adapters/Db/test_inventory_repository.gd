extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func before() -> void:
    var helper = preload("res://Game.Godot/Adapters/Db/DbTestHelper.cs").new()
    add_child(auto_free(helper))
    helper.ForceManaged()
    var db = null
    if ClassDB.class_exists("SqliteDataStore"):
        db = ClassDB.instantiate("SqliteDataStore")
    else:
        var s = load("res://Game.Godot/Adapters/SqliteDataStore.cs")
        db = Node.new()
        db.set_script(s)
    db.name = "SqlDb"
    get_tree().get_root().add_child(auto_free(db))
    var path := "user://utdb_%s/game.db" % Time.get_unix_time_from_system()
    if not db.TryOpen(path):
        push_warning("SKIP: " + str(db.LastError))
        return
    helper.CreateSchema()
    helper.ClearAll()

func test_inventory_add_and_list() -> void:
    var bridge = preload("res://Game.Godot/Adapters/Db/InventoryRepoBridge.cs").new()
    add_child(auto_free(bridge))
    var ok = bridge.Add("potion", 2)
    assert_bool(ok).is_true()
    var items = bridge.All()
    assert_int(int(items.size())).is_greater(0)
