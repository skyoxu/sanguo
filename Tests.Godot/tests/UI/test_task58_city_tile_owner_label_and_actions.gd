extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const HUD_CANDIDATE_PATHS: Array[String] = [
	"res://Game.Godot/Scripts/UI/HUD.cs",
	"res://Game.Godot/Scripts/UI/Hud.cs",
	"res://Scripts/UI/HUD.cs",
	"res://Scripts/UI/Hud.cs",
]

const CORE_EVENTS_CANDIDATE_PATHS: Array[String] = [
	"res://Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs",
	"res://Contracts/Sanguo/SanguoModuleEvents.cs",
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

func _contains_all(haystack: String, needles: Array[String]) -> bool:
	for needle in needles:
		if haystack.find(needle) == -1:
			return false
	return true

# ACC:T58.3
# UI contract smoke: HUD has owner/actions entry points discoverable in source.
func test_task58_owner_label_and_actions_contract_smoke() -> void:
	var hud_path := _first_existing_path(HUD_CANDIDATE_PATHS)
	assert_bool(not hud_path.is_empty()).is_true()

	var hud_source := _read_text_or_empty(hud_path)
	assert_bool(hud_source.length() > 0).is_true()
	assert_bool(_contains_all(hud_source, ["ShowTileActionPanel", "PublishTileActionSelected"])).is_true()

# ACC:T58.4
# Observable result smoke: building built event contract type string exists.
func test_task58_action_observable_result_contract_smoke() -> void:
	var events_path := _first_existing_path(CORE_EVENTS_CANDIDATE_PATHS)
	assert_bool(not events_path.is_empty()).is_true()

	var events_source := _read_text_or_empty(events_path)
	assert_bool(events_source.length() > 0).is_true()
	assert_bool(events_source.find("core.sanguo.building.built") != -1).is_true()
