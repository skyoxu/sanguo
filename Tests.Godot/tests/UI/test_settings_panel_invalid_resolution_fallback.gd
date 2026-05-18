extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CFG_PATH := "user://settings.cfg"

var _last_valid_resolution: Vector2i = Vector2i.ZERO
var _saved_window_mode_text := ""

func _on_resolution_applied(effective: Vector2i) -> void:
	_last_valid_resolution = effective

# ACC:T29.6
# ACC:T188.1 ACC:T188.2 ACC:T188.3 ACC:T188.4 ACC:T188.5 ACC:T188.8 ACC:T188.10 ACC:T188.11
# Acceptance intent: invalid/unsupported resolution must not crash and should fall back to last valid.
func test_invalid_resolution_in_config_falls_back_to_last_valid_and_ui_matches_effective() -> void:
	# Clear config.
	var dir := DirAccess.open("user://")
	if dir != null and dir.file_exists("settings.cfg"):
		dir.remove("settings.cfg")

	var packed := load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn") as PackedScene
	assert_bool(packed != null).is_true()
	if packed == null:
		return

	var panel = packed.instantiate()
	add_child(auto_free(panel))
	await get_tree().process_frame

	var res_opt := panel.get_node("Center/VBox/ResolutionRow/ResolutionOpt")
	assert_bool(res_opt != null).is_true()
	if res_opt == null:
		return
	assert_bool(res_opt.get_item_count() > 0).is_true()

	var mode_opt := panel.get_node("Center/VBox/WindowModeRow/WindowModeOpt") as OptionButton
	assert_bool(mode_opt != null).is_true()
	if mode_opt == null:
		return
	assert_bool(mode_opt.get_item_count() > 0).is_true()

	_last_valid_resolution = Vector2i.ZERO
	panel.connect("ResolutionApplied", Callable(self, "_on_resolution_applied"))

	# Save a valid resolution first (establish last_valid in product code).
	res_opt.select(0)
	mode_opt.select(0)
	await get_tree().process_frame
	panel.get_node("Center/VBox/Buttons/SaveBtn").emit_signal("pressed")
	await get_tree().process_frame
	assert_bool(_last_valid_resolution.x > 0 and _last_valid_resolution.y > 0).is_true()
	_saved_window_mode_text = mode_opt.get_item_text(mode_opt.selected)

	# Corrupt config with an invalid resolution and trigger Load.
	var cfg = ConfigFile.new()
	var err := cfg.load(CFG_PATH)
	assert_int(err).is_equal(OK)
	cfg.set_value("settings", "resolution", "0x0")
	cfg.set_value("settings", "window_mode", "invalid")
	err = cfg.save(CFG_PATH)
	assert_int(err).is_equal(OK)

	# Move away from the saved selection to prove Load updates UI.
	var other: int = 0 if res_opt.get_item_count() <= 1 else 1
	res_opt.select(other)
	mode_opt.select(min(1, mode_opt.get_item_count() - 1))
	await get_tree().process_frame

	panel.call("ShowPanel")
	await get_tree().process_frame

	var expected_text: String = "%dx%d" % [_last_valid_resolution.x, _last_valid_resolution.y]
	assert_str(res_opt.get_item_text(res_opt.selected)).is_equal(expected_text)
	assert_str(mode_opt.get_item_text(mode_opt.selected)).is_equal(_saved_window_mode_text)
