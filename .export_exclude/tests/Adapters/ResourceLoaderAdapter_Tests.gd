extends GdUnitTestSuite

func test_resource_loader_can_read_project_file() -> void:
    var loader = preload("res://Game.Godot/Adapters/ResourceLoaderAdapter.cs").new()
    add_child(loader)
    var txt = loader.LoadText("res://project.godot")
    assert_str(txt).contains("[application]")
    loader.queue_free()

func test_resource_loader_can_read_bytes() -> void:
    var loader = preload("res://Game.Godot/Adapters/ResourceLoaderAdapter.cs").new()
    add_child(loader)
    var bytes = loader.LoadBytes("res://icon.svg")
    assert_object(bytes).is_not_null()
    assert_int(int(bytes.size())).is_greater(0)
    loader.queue_free()

func test_resource_loader_rejects_unsafe_paths() -> void:
    var loader = preload("res://Game.Godot/Adapters/ResourceLoaderAdapter.cs").new()
    add_child(loader)
    var txt = loader.LoadText("C:/Windows/System32/drivers/etc/hosts")
    assert_object(txt).is_null()
    loader.queue_free()

