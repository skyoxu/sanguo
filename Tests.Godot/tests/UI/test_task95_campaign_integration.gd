extends "res://tests/UI/_fixtures/test_ui_event_log_fixture.gd"

const EVENT_GAME_STARTED := "core.sanguo.game.started"
const EVENT_BOSS_CHALLENGE_PROMPTED := "core.sanguo.boss.challenge.prompted"
const KEY_GAME_START_CONFIG := "game_start_config"

func before_test() -> void:
	await _setup_event_bus()

func after_test() -> void:
	await _teardown_event_bus()

func _publish_game_started(config_payload: String) -> void:
	var payload := "{\"game_start_config\":%s}" % config_payload
	_bus.PublishSimple(EVENT_GAME_STARTED, "ut", payload)

func _publish_boss_prompted() -> void:
	_bus.PublishSimple(
		EVENT_BOSS_CHALLENGE_PROMPTED,
		"ut",
		"{\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":3,\"NextRoundPressureForecast\":2}"
	)

func _campaign_panel_label(hud: Node, name: String) -> Label:
	return hud.get_node("TopBar/TopStack/CampaignParamsPanel/VBox/%s" % name) as Label

func _wait_hud_frames(count: int = 4) -> void:
	for _i in range(count):
		await get_tree().process_frame

# ACC:T95.1
# ACC:T95.2
func test_task95_campaign_parameter_panel_shows_localized_values_from_runtime_state() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()

	_publish_game_started(
		"{\"run_mode\":\"campaign\",\"commander_id\":\"c_liu_bei\",\"difficulty\":\"normal\",\"active_strategem_id\":\"strat_active_default\",\"passive_strategem_id\":\"strat_passive_default\"}"
	)
	_publish_boss_prompted()
	await _wait_hud_frames()

	var commander_label := _campaign_panel_label(hud, "CommanderValue")
	var strategem_label := _campaign_panel_label(hud, "StrategemsValue")
	var difficulty_label := _campaign_panel_label(hud, "DifficultyValue")
	var round_label := _campaign_panel_label(hud, "RoundValue")
	var pressure_label := _campaign_panel_label(hud, "BossPressureValue")

	assert_str(commander_label.text).contains("Liu Bei")
	assert_str(strategem_label.text).contains("Default Active")
	assert_str(strategem_label.text).contains("Default Passive")
	assert_str(difficulty_label.text).contains("Normal")
	assert_str(round_label.text).contains("R3")
	assert_str(pressure_label.text).contains("Yellow Turban Leader")
	assert_str(pressure_label.text).contains("+2")

	_restore_locale(original_locale)

# ACC:T95.1
# ACC:T95.2
func test_task95_campaign_parameter_panel_shows_localized_values_from_runtime_state_in_zh() -> void:
	var original_locale := _set_locale("zh-CN")
	var hud := await _hud()

	_publish_game_started(
		"{\"run_mode\":\"campaign\",\"commander_id\":\"c_liu_bei\",\"difficulty\":\"normal\",\"active_strategem_id\":\"strat_active_default\",\"passive_strategem_id\":\"strat_passive_default\"}"
	)
	_publish_boss_prompted()
	await _wait_hud_frames()

	var commander_label := _campaign_panel_label(hud, "CommanderValue")
	var strategem_label := _campaign_panel_label(hud, "StrategemsValue")
	var difficulty_label := _campaign_panel_label(hud, "DifficultyValue")
	var round_label := _campaign_panel_label(hud, "RoundValue")
	var pressure_label := _campaign_panel_label(hud, "BossPressureValue")

	assert_str(commander_label.text).contains("刘备")
	assert_str(strategem_label.text).contains("默认主动")
	assert_str(strategem_label.text).contains("默认被动")
	assert_str(strategem_label.text).not_contains("Default Active")
	assert_str(difficulty_label.text).contains("普通")
	assert_str(difficulty_label.text).not_contains("Normal")
	assert_str(round_label.text).contains("R3")
	assert_str(pressure_label.text).contains("黄巾首领")
	assert_str(pressure_label.text).contains("+2")
	assert_str(pressure_label.text).not_contains("Yellow Turban Leader")

	_restore_locale(original_locale)

# ACC:T95.3
func test_task95_release_mode_hides_raw_tokens_and_localization_keys() -> void:
	var original_locale := _set_locale("en")
	var hud := await _hud()

	_publish_game_started(
		"{\"run_mode\":\"campaign\",\"commander_id\":\"character.c_missing.name\",\"difficulty\":\"ui.menu.difficulty.unknown\",\"active_strategem_id\":\"strat.missing.active\",\"passive_strategem_id\":\"strat.missing.passive\"}"
	)
	await _wait_hud_frames()

	var commander_label := _campaign_panel_label(hud, "CommanderValue")
	var strategem_label := _campaign_panel_label(hud, "StrategemsValue")
	var difficulty_label := _campaign_panel_label(hud, "DifficultyValue")
	var pressure_label := _campaign_panel_label(hud, "BossPressureValue")

	assert_str(commander_label.text).is_not_equal("character.c_missing.name")
	assert_str(commander_label.text).contains("Unknown")
	assert_str(strategem_label.text).contains("Unknown")
	assert_str(strategem_label.text).is_not_equal("strat.missing.active / strat.missing.passive")
	assert_str(difficulty_label.text).contains("Unknown")
	assert_str(difficulty_label.text).is_not_equal("ui.menu.difficulty.unknown")
	assert_str(pressure_label.text).contains("No boss pressure")

	_restore_locale(original_locale)
