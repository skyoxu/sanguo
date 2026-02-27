extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

var _last_emitted_type := ""

func before_test() -> void:
	await _setup_event_bus()
	_connect_domain_event_emitted(Callable(self, "_on_domain_event_emitted"))
	_last_emitted_type = ""

func after_test() -> void:
	await _teardown_event_bus()

func _on_domain_event_emitted(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
	_last_emitted_type = str(type)

func test_settings_menu_pauses_and_resumes_game() -> void:
	var hud = await _hud()
	var menu: Control = hud.get_node("SettingsMenu")
	var btn_settings: Button = hud.get_node("TopBar/TopStack/HBox/GameSettingsButton")
	var btn_resume: Button = hud.get_node("SettingsMenu/Center/Panel/VBox/BtnResume")

	assert_bool(menu.visible).is_false()
	assert_bool(get_tree().paused).is_false()

	btn_settings.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(get_tree().paused).is_true()
	assert_bool(menu.is_visible_in_tree()).is_true()

	btn_resume.emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(get_tree().paused).is_false()
	assert_bool(menu.visible).is_false()

func test_settings_menu_emits_save_load_and_quit_events() -> void:
	var hud = await _hud()
	var btn_settings: Button = hud.get_node("TopBar/TopStack/HBox/GameSettingsButton")
	var btn_save: Button = hud.get_node("SettingsMenu/Center/Panel/VBox/BtnSave")
	var btn_load: Button = hud.get_node("SettingsMenu/Center/Panel/VBox/BtnLoad")
	var btn_quit: Button = hud.get_node("SettingsMenu/Center/Panel/VBox/BtnQuit")

	btn_settings.emit_signal("pressed")
	await get_tree().process_frame

	_last_emitted_type = ""
	btn_save.emit_signal("pressed")
	await get_tree().process_frame
	assert_str(_last_emitted_type).is_equal("ui.hud.save")

	_last_emitted_type = ""
	btn_load.emit_signal("pressed")
	await get_tree().process_frame
	assert_str(_last_emitted_type).is_equal("ui.hud.load")

	_last_emitted_type = ""
	btn_quit.emit_signal("pressed")
	await get_tree().process_frame
	assert_str(_last_emitted_type).is_equal("ui.menu.quit")
