extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const HUD_CANDIDATE_PATHS: Array[String] = [
	"res://Game.Godot/Scripts/UI/HUD.cs",
	"res://Game.Godot/Scripts/UI/Hud.cs",
	"res://Scripts/UI/HUD.cs",
	"res://Scripts/UI/Hud.cs",
]

func _first_existing_path(paths: Array[String]) -> String:
	for path in paths:
		if FileAccess.file_exists(path):
			return path
	return ""

func _read_text_or_empty(path: String) -> String:
	if path.is_empty():
		return ""
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return ""
	var text := file.get_as_text()
	file.close()
	return text

# ACC:T58.3
# Red-first: before Task58 implementation, HUD is expected to NOT provide an explicit "build" action id.
# This test will turn green when HUD supports an explicit build action id for owned-city landing.
func test_task58_hud_should_support_build_action_id() -> void:
	var hud_path := _first_existing_path(HUD_CANDIDATE_PATHS)
	assert_bool(not hud_path.is_empty()).is_true()

	var hud_source := _read_text_or_empty(hud_path)
	assert_bool(hud_source.length() > 0).is_true()

	# Intentionally strict: require an explicit action id token to exist in HUD source.
	assert_bool(hud_source.find("\"build\"") != -1).is_true()
