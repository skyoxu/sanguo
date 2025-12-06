extends GdUnitTestSuite


func test_smoke_passes() -> void:
	assert_int(1 + 1).is_equal(2)

