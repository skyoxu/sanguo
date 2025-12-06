extends GdUnitTestSuite

func test_datastore_save_load_delete() -> void:
    var ds = get_node_or_null("/root/DataStore")
    assert_object(ds).is_not_null()

    var key = "ut_" + str(Time.get_ticks_msec())
    ds.SaveSync(key, "{\"hello\":\"world\"}")
    var loaded = ds.LoadSync(key)
    assert_str(loaded).contains("hello")
    ds.DeleteSync(key)
    var after = ds.LoadSync(key)
    assert_str(str(after)).is_equal("null")

