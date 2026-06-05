extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _status_text(hud: Node, label_name: String) -> String:
	var label := hud.get_node_or_null("TopBar/TopStack/CampaignParamsPanel/VBox/ResponseStatusPanel/%s" % label_name) as Label
	assert_object(label).is_not_null()
	assert_bool(label.visible).is_true()
	return str(label.text)

# ACC:T200.1 ACC:T200.2 ACC:T200.3 ACC:T200.4 ACC:T200.5 ACC:T200.6 ACC:T200.7 ACC:T200.8
func test_task200_response_status_surface_renders_all_governed_statuses_and_unavailable_states() -> void:
	var hud := await _hud()
	var panel := hud.get_node_or_null("TopBar/TopStack/CampaignParamsPanel/VBox/ResponseStatusPanel") as Control
	assert_object(panel).is_not_null()
	assert_bool(panel.visible).is_true()

	assert_str(_status_text(hud, "PersistenceStatus")).contains("Persistence")
	assert_str(_status_text(hud, "LocalizationStatus")).contains("Localization")
	assert_str(_status_text(hud, "AudioStatus")).contains("Audio")
	assert_str(_status_text(hud, "PerformanceStatus")).contains("Performance")
	assert_str(_status_text(hud, "PlatformStatus")).contains("Platform")
	assert_str(_status_text(hud, "PersistenceStatus")).contains("unavailable")
	assert_str(_status_text(hud, "LocalizationStatus")).contains("unavailable")
	assert_str(_status_text(hud, "AudioStatus")).contains("unavailable")
	assert_str(_status_text(hud, "PerformanceStatus")).contains("degraded")
	assert_str(_status_text(hud, "PlatformStatus")).contains("Windows")

	var status := {
		"persistence": "saved",
		"localization": "en active",
		"audio": "active",
		"performance": "degraded",
		"platform": "Windows supported"
	}
	assert_bool(hud.has_method("UpdateResponseStatusSurface")).is_true()
	hud.call("UpdateResponseStatusSurface", status)
	await get_tree().process_frame

	assert_str(_status_text(hud, "PersistenceStatus")).contains("saved")
	assert_str(_status_text(hud, "LocalizationStatus")).contains("en active")
	assert_str(_status_text(hud, "AudioStatus")).contains("active")
	assert_str(_status_text(hud, "PerformanceStatus")).contains("degraded")
	assert_str(_status_text(hud, "PlatformStatus")).contains("Windows supported")

	status["persistence"] = "failed: disk unavailable"
	status["localization"] = "unsupported locale"
	status["audio"] = "inactive adapter"
	status["performance"] = "unavailable"
	status["platform"] = "unsupported"
	hud.call("UpdateResponseStatusSurface", status)
	await get_tree().process_frame

	assert_str(_status_text(hud, "PersistenceStatus")).contains("failed")
	assert_str(_status_text(hud, "PersistenceStatus")).not_contains("saved")
	assert_str(_status_text(hud, "LocalizationStatus")).contains("unsupported")
	assert_str(_status_text(hud, "AudioStatus")).contains("inactive")
	assert_str(_status_text(hud, "PerformanceStatus")).contains("unavailable")
	assert_str(_status_text(hud, "PlatformStatus")).contains("unsupported")

# ACC:T200.2 ACC:T200.3 ACC:T200.4 ACC:T200.5 ACC:T200.6 ACC:T200.7 ACC:T200.8
func test_task200_response_status_surface_updates_from_event_bus_status_sources() -> void:
	var hud := await _hud()

	_bus.PublishSimple(
		"ui.hud.response.status.updated",
		"gdunit",
		"{\"persistence\":\"pending\",\"localization\":\"zh active\",\"audio\":\"inactive adapter\",\"performance\":\"degraded\",\"platform\":\"Windows supported\"}"
	)
	await get_tree().process_frame

	assert_str(_status_text(hud, "PersistenceStatus")).contains("pending")
	assert_str(_status_text(hud, "LocalizationStatus")).contains("zh active")
	assert_str(_status_text(hud, "AudioStatus")).contains("inactive")
	assert_str(_status_text(hud, "PerformanceStatus")).contains("degraded")
	assert_str(_status_text(hud, "PlatformStatus")).contains("Windows supported")

	_bus.PublishSimple(
		"core.sanguo.game.saved",
		"gdunit",
		"{\"GameId\":\"g1\",\"SaveSlotId\":\"quick\",\"CorrelationId\":\"corr-save\"}"
	)
	await get_tree().process_frame
	assert_str(_status_text(hud, "PersistenceStatus")).contains("saved")

	_bus.PublishSimple(
		"core.save.write.failed",
		"gdunit",
		"{\"Reason\":\"disk unavailable\",\"CorrelationId\":\"corr-fail\"}"
	)
	await get_tree().process_frame
	assert_str(_status_text(hud, "PersistenceStatus")).contains("failed")
	assert_str(_status_text(hud, "PersistenceStatus")).contains("disk unavailable")
	assert_str(_status_text(hud, "PersistenceStatus")).not_contains("saved")
