extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_GAME_STARTED := "core.sanguo.game.started"
const EVENT_TURN_STARTED := "core.sanguo.game.turn.started"
const EVENT_TOKEN_MOVED := "core.sanguo.board.token.moved"
const EVENT_CITY_BOUGHT := "core.sanguo.city.bought"
const EVENT_COMBAT_STARTED := "core.sanguo.combat.started"
const EVENT_GAME_ENDED := "core.sanguo.game.ended"
const LOCALE_EN := "en"

const GUIDE_PANEL_PATH := "GuideHintPanel"
const GUIDE_TITLE_PATH := "GuideHintPanel/VBox/GuideTitle"
const GUIDE_TEXT_PATH := "GuideHintPanel/VBox/GuideText"
const GUIDE_OVERLAY_PATH := "GuideOverlay"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _guide_panel(hud: Node) -> Control:
	return hud.get_node(GUIDE_PANEL_PATH)

func _guide_title(hud: Node) -> Label:
	return hud.get_node(GUIDE_TITLE_PATH)

func _guide_text(hud: Node) -> Label:
	return hud.get_node(GUIDE_TEXT_PATH)

func _guide_overlay(hud: Node) -> Control:
	return hud.get_node(GUIDE_OVERLAY_PATH)

func _overlay_rect(hud: Node) -> Rect2:
	var overlay := _guide_overlay(hud)
	if overlay.has_method("GetHighlightRect"):
		return overlay.call("GetHighlightRect")
	return Rect2()

func _hud() -> Node:
	var packed := ResourceLoader.load("res://Game.Godot/Scenes/UI/HUD.tscn", "", ResourceLoader.CACHE_MODE_IGNORE)
	assert_bool(packed != null).is_true()
	var scene := packed as PackedScene
	assert_bool(scene != null).is_true()
	var hud = scene.instantiate()
	add_child(hud)
	await get_tree().process_frame
	return hud

func _normalize_text(text: String) -> String:
	var filtered := ""
	for i in range(text.length()):
		var ch := text[i]
		var code := ch.unicode_at(0)
		if code <= 32:
			continue
		if code == 0x00A0 or code == 0x202F or code == 0x2007 or code == 0x2009 or code == 0x200A or code == 0x200B:
			continue
		filtered += String(ch)
	return filtered

func _wait_for_tokens(hud: Node, tokens: PackedStringArray, max_frames: int = 60) -> void:
	var expected: Array = []
	for token in tokens:
		expected.append(_normalize_text(String(token)).to_lower())
	for _i in range(max_frames):
		var current := _normalize_text(String(_guide_text(hud).text)).to_lower()
		var ok := true
		for token in expected:
			if current.find(String(token)) == -1:
				ok = false
				break
		if ok:
			return
		await get_tree().process_frame
	var latest := _normalize_text(String(_guide_text(hud).text)).to_lower()
	for token in expected:
		assert_str(latest).contains(String(token))

func _wait_for_visible(panel: Control, max_frames: int = 60) -> void:
	for _i in range(max_frames):
		if panel.visible:
			return
		await get_tree().process_frame
	assert_bool(panel.visible).is_true()

# ACC:T60.3
func test_newbie_guide_hint_updates_on_core_events() -> void:
	var original_locale := _set_locale(LOCALE_EN)
	var hud := await _hud()

	var panel := _guide_panel(hud)
	assert_bool(panel.visible).is_false()

	_bus.PublishSimple(EVENT_GAME_STARTED, "ut", "{\"game_start_config\":{\"character_assignments\":{}}}")
	await _wait_for_tokens(hud, ["01/06", "start", "seed"])
	await _wait_for_visible(panel)
	assert_str(_normalize_text(String(_guide_text(hud).text))).not_contains("help.tutorial.step")

	_bus.PublishSimple(EVENT_TURN_STARTED, "ut", "{\"ActivePlayerId\":\"p1\",\"Year\":1,\"Month\":1,\"Day\":1}")
	await _wait_for_tokens(hud, ["02/06", "beforeroll", "cards"])
	var overlay := _guide_overlay(hud)
	assert_bool(overlay.visible).is_true()
	var rect := _overlay_rect(hud)
	assert_bool(rect.size.x > 0 and rect.size.y > 0).is_true()

	_bus.PublishSimple(EVENT_TOKEN_MOVED, "ut", "{\"PlayerId\":\"p1\",\"FromIndex\":0,\"ToIndex\":1,\"Steps\":1}")
	await _wait_for_tokens(hud, ["03/06", "tile", "global"])

	_bus.PublishSimple(EVENT_CITY_BOUGHT, "ut", "{\"BuyerId\":\"p1\",\"CityId\":\"tile_01\"}")
	await _wait_for_tokens(hud, ["04/06", "build", "multipliers"])

	_bus.PublishSimple(EVENT_COMBAT_STARTED, "ut", "{\"GameId\":\"g1\",\"PlayerId\":\"p1\",\"EncounterId\":\"enc_01\",\"RandomSeed\":1}")
	await _wait_for_tokens(hud, ["05/06", "combat"])

	_bus.PublishSimple(EVENT_GAME_ENDED, "ut", "{\"GameId\":\"g1\",\"EndReason\":\"player_bankrupt\"}")
	await _wait_for_tokens(hud, ["06/06", "game.ended"])

	assert_str(_normalize_text(String(_guide_title(hud).text)).to_lower()).contains("learning")

	_restore_locale(original_locale)
