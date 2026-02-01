extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func test_result_popup_shows_for_city_bought_event() -> void:
	var hud = await _hud()
	var popup: Control = hud.get_node("EventResultPopup")
	var message: Label = popup.get_node("Center/Panel/VBox/Message")
	popup.AutoHideSeconds = 0.0

	assert_bool(popup.visible).is_false()

	_bus.PublishSimple("core.sanguo.city.bought", "ut", "{\"GameId\":\"g1\",\"BuyerId\":\"p1\",\"CityId\":\"tile_01\",\"Price\":100}")
	for _i in range(30):
		await get_tree().process_frame
		if popup.visible:
			break

	assert_bool(popup.visible).is_true()
	assert_bool(message.text.strip_edges().length() > 0).is_true()
