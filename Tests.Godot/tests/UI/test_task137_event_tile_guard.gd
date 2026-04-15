extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const GUARD_ADAPTER := preload("res://Game.Godot/Scripts/UI/EventTileAutoTriggerGuardAdapter.cs")


func _new_guard() -> Object:
	return GUARD_ADAPTER.new()


# acceptance: ACC:T137.1
func test_landing_on_event_tile_immediately_enters_mandatory_resolution() -> void:
	var guard := _new_guard()
	guard.LandOnTile("event", "rebellion")

	assert(guard.InEventResolution, "Landing on an event tile must immediately enter mandatory event resolution.")
	assert(not guard.TrySkip(), "Skip must already be blocked once event resolution starts.")


# acceptance: ACC:T137.2
func test_skip_and_unrelated_actions_are_refused_during_event_resolution() -> void:
	var guard := _new_guard()
	guard.EnterResolution("rebellion")
	var still_in_resolution := bool(guard.InEventResolution)

	assert(not guard.TrySkip(), "Skip must be refused during event resolution.")
	assert(not guard.TryEndTurn(), "End-turn must be refused during event resolution.")
	assert(not guard.TryOpenShop(), "Unrelated actions must be refused during event resolution.")
	assert(bool(guard.InEventResolution) == still_in_resolution, "Refused actions must not change resolution state.")


# acceptance: ACC:T137.3
func test_popup_text_and_event_name_are_localized_on_auto_trigger() -> void:
	var guard := _new_guard()
	guard.LandOnTile("event", "rebellion")

	assert(guard.TriggeredEventName == "Rebellion Uprising", "Auto-trigger must expose localized event name.")
	assert(guard.PopupText == "Event Triggered: Rebellion Uprising", "Popup text must include localized event name.")
