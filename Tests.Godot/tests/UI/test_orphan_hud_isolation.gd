extends "res://tests/UI/_fixtures/ui_event_log_fixture.gd"

const LOG_FILE_NAME := "ui_orphan_isolation.jsonl"

func before_test() -> void:
	pass

func after_test() -> void:
	await _teardown_event_bus()

func _orphan_count() -> int:
	return int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))

func _append_log(entry: Dictionary) -> void:
	var date := Time.get_date_string_from_system()
	var dir_path := "user://logs/e2e/%s" % date
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir_path))
	var file_path := "%s/%s" % [dir_path, LOG_FILE_NAME]
	var file := FileAccess.open(file_path, FileAccess.READ_WRITE)
	if file == null:
		file = FileAccess.open(file_path, FileAccess.WRITE)
	if file == null:
		return
	file.seek_end()
	file.store_string(JSON.stringify(entry))
	file.store_string("\n")
	file.flush()

func test_hud_orphan_count_delta_is_zero() -> void:
	var baseline := _orphan_count()
	await _setup_event_bus()
	await get_tree().process_frame
	var after_bus := _orphan_count()

	var _hud_instance = await _hud()
	await get_tree().process_frame
	assert_bool(_hud_instance.is_inside_tree()).is_true()
	var after_hud := _orphan_count()

	await _teardown_event_bus()
	await get_tree().process_frame
	var after_teardown := _orphan_count()
	var delta := after_teardown - baseline

	_append_log({
		"ts": Time.get_datetime_string_from_system(),
		"baseline": baseline,
		"after_bus": after_bus,
		"after_hud": after_hud,
		"after_teardown": after_teardown,
		"delta": delta,
		"scene": "HUD"
	})

	assert_int(delta).is_equal(0)

func test_event_log_panel_orphan_count_delta_is_zero() -> void:
	var baseline := _orphan_count()
	var panel = preload("res://Game.Godot/Scenes/UI/EventLogPanel.tscn").instantiate()
	add_child(panel)
	await get_tree().process_frame
	var after_create := _orphan_count()
	panel.queue_free()
	await get_tree().process_frame
	var after_teardown := _orphan_count()
	var delta := after_teardown - baseline

	_append_log({
		"ts": Time.get_datetime_string_from_system(),
		"baseline": baseline,
		"after_create": after_create,
		"after_teardown": after_teardown,
		"delta": delta,
		"scene": "EventLogPanel"
	})

	assert_int(delta).is_equal(0)

func test_event_toast_orphan_count_delta_is_zero() -> void:
	var baseline := _orphan_count()
	var toast = preload("res://Game.Godot/Scenes/UI/EventToast.tscn").instantiate()
	add_child(toast)
	await get_tree().process_frame
	var after_create := _orphan_count()
	toast.queue_free()
	await get_tree().process_frame
	var after_teardown := _orphan_count()
	var delta := after_teardown - baseline

	_append_log({
		"ts": Time.get_datetime_string_from_system(),
		"baseline": baseline,
		"after_create": after_create,
		"after_teardown": after_teardown,
		"delta": delta,
		"scene": "EventToast"
	})

	assert_int(delta).is_equal(0)
