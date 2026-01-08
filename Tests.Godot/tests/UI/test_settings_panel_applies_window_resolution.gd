extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const CFG_PATH := "user://settings.cfg"

var _resolution_applied := false
var _last_resolution: Vector2i = Vector2i.ZERO

func _on_resolution_applied(effective: Vector2i) -> void:
	_resolution_applied = true
	_last_resolution = effective

# ACC:T29.5
func test_settings_panel_applies_window_resolution_via_settings_panel_and_persists() -> void:
	# Ensure config does not interfere with this test.
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

	_resolution_applied = false
	_last_resolution = Vector2i.ZERO
	panel.connect("ResolutionApplied", Callable(self, "_on_resolution_applied"))

	var res_opt := panel.get_node("VBox/ResolutionRow/ResolutionOpt") as OptionButton
	assert_bool(res_opt != null).is_true()
	if res_opt == null:
		return
	assert_bool(res_opt.get_item_count() > 0).is_true()

	var saved_text: String = res_opt.get_item_text(res_opt.selected)
	# Choose a deterministic item (0) and save it.
	res_opt.select(0)
	await get_tree().process_frame
	saved_text = res_opt.get_item_text(res_opt.selected)

	panel.get_node("VBox/Buttons/SaveBtn").emit_signal("pressed")
	await get_tree().process_frame

	# Change selection to prove Load restores it.
	var other: int = 0 if res_opt.get_item_count() <= 1 else 1
	res_opt.select(other)
	await get_tree().process_frame

	panel.get_node("VBox/Buttons/LoadBtn").emit_signal("pressed")
	await get_tree().process_frame

	assert_str(res_opt.get_item_text(res_opt.selected)).is_equal(saved_text)
	assert_bool(_resolution_applied).is_true()
	assert_bool(_last_resolution.x > 0 and _last_resolution.y > 0).is_true()

	# Validate persisted value exists.
	var cfg = ConfigFile.new()
	var err := cfg.load(CFG_PATH)
	assert_int(err).is_equal(OK)
	assert_str(str(cfg.get_value("settings", "resolution", ""))).is_equal(saved_text)
