extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _capability_text(hud: Node) -> String:
	var label := hud.get_node_or_null("TopBar/TopStack/CampaignParamsPanel/VBox/ResponseStatusPanel/CompletedCapabilityList") as Label
	assert_object(label).is_not_null()
	assert_bool(label.visible).is_true()
	return str(label.text)

# ACC:T202.1
# ACC:T202.2
# ACC:T202.3
# ACC:T202.5
# ACC:T202.6
func test_task202_completed_capability_surface_renders_completion_and_ownership_scope() -> void:
	var hud := await _hud()
	assert_bool(hud.has_method("UpdateCompletedCapabilitySurface")).is_true()

	var capabilities := [
		{
			"id": "T196",
			"title": "Chapter 7 completion count",
			"completion_state": "completed",
			"owner": "chapter7",
			"responsibility": "completed task count evidence"
		},
		{
			"id": "T201",
			"title": "Visible state ownership",
			"completion_state": "completed",
			"owner": "gameplay",
			"responsibility": "visible save and audit ownership"
		}
	]
	hud.call("UpdateCompletedCapabilitySurface", capabilities)
	await get_tree().process_frame

	var text := _capability_text(hud)
	assert_str(text).contains("T196")
	assert_str(text).contains("Chapter 7 completion count")
	assert_str(text).contains("completed")
	assert_str(text).contains("owner: chapter7")
	assert_str(text).contains("responsibility: completed task count evidence")
	assert_str(text).contains("T201")
	assert_str(text).contains("owner: gameplay")

# ACC:T202.7
# ACC:T202.8
# ACC:T202.9
# ACC:T202.10
func test_task202_completed_capability_surface_refuses_missing_source_or_ownership_status() -> void:
	var hud := await _hud()
	assert_bool(hud.has_method("UpdateCompletedCapabilitySurface")).is_true()

	var previous := [
		{
			"id": "T196",
			"title": "Chapter 7 completion count",
			"completion_state": "completed",
			"owner": "chapter7",
			"responsibility": "completed task count evidence"
		}
	]
	hud.call("UpdateCompletedCapabilitySurface", previous)
	await get_tree().process_frame
	var before_text := _capability_text(hud)

	var invalid := [
		{
			"id": "T202",
			"title": "Missing ownership status",
			"completion_state": "completed"
		},
		{
			"title": "Missing completed source",
			"completion_state": "completed",
			"owner": "gameplay"
		}
	]
	hud.call("UpdateCompletedCapabilitySurface", invalid)
	await get_tree().process_frame

	var text := _capability_text(hud)
	assert_str(text).not_contains("T202: completed")
	assert_str(text).not_contains("Missing completed source: completed")
	assert_bool(text == before_text or text.find("unavailable") != -1 or text.find("refusal") != -1).is_true()

# ACC:T202.8
func test_task202_completed_capability_surface_shows_unavailable_state_for_empty_source() -> void:
	var hud := await _hud()
	assert_bool(hud.has_method("UpdateCompletedCapabilitySurface")).is_true()

	hud.call("UpdateCompletedCapabilitySurface", [])
	await get_tree().process_frame

	var text := _capability_text(hud)
	assert_str(text).contains("Completed Capabilities")
	assert_str(text).contains("unavailable")
