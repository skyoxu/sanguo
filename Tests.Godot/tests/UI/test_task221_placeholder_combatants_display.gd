extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const EVENT_COMBAT_STARTED := "core.sanguo.combat.started"
const EVENT_COMBAT_ENDED := "core.sanguo.combat.ended"

var _bus: Node

func before() -> void:
	var existing := get_node_or_null("/root/EventBus")
	if existing != null:
		existing.name = "EventBus__old__%s" % str(Time.get_ticks_msec())
		existing.queue_free()

	_bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
	_bus.name = "EventBus"
	get_tree().get_root().add_child(auto_free(_bus))

func _battle_view() -> Control:
	var view := preload("res://Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn").instantiate()
	add_child(auto_free(view))
	await get_tree().process_frame
	return view

func _details_text(view: Control) -> String:
	var details: Label = view.get_node("Panel/VBox/Details")
	return str(details.text)

func _started_payload_with_placeholders() -> Dictionary:
	return {
		"GameId": "g1",
		"PlayerId": "p1",
		"EncounterId": "enc_221",
		"RandomSeed": 7,
		"OccurredAt": "2026-01-01T00:00:00Z",
		"CorrelationId": "corr-221",
		"CausationId": "ui.sanguo.tile.action.selected",
		"PlayerSnapshot": {
			"MainUnit": {
				"UnitId": "p1-main",
				"DisplayName": "Player Placeholder",
				"UnitRole": "player",
				"Stats": {
					"MaxHP": 100,
					"CurrentHP": 98,
					"Attack": 12
				},
				"SkillIds": ["skill_basic_strike"],
				"PassiveSkillIds": [],
				"RelicIds": [],
				"BuffIds": ["buff_ready"],
				"DebuffIds": []
			}
		},
		"EnemySnapshot": {
			"MainUnit": {
				"UnitId": "enemy-enc_221",
				"DisplayName": "Enemy Placeholder",
				"UnitRole": "enemy",
				"Stats": {
					"MaxHP": 88,
					"CurrentHP": 88,
					"Attack": 11
				},
				"SkillIds": [],
				"PassiveSkillIds": [],
				"RelicIds": [],
				"BuffIds": [],
				"DebuffIds": ["debuff_exposed"]
			}
		}
	}

func _ended_payload_with_placeholders() -> Dictionary:
	var snapshot_player := {
		"MainUnit": {
			"UnitId": "p1-main",
			"DisplayName": "Player Placeholder",
			"UnitRole": "player",
			"Stats": {
				"MaxHP": 100,
				"CurrentHP": 96,
				"Attack": 12
			},
			"SkillIds": ["skill_basic_strike"],
			"PassiveSkillIds": [],
			"RelicIds": [],
			"BuffIds": ["buff_ready"],
			"DebuffIds": []
		}
	}
	var snapshot_enemy := {
		"MainUnit": {
			"UnitId": "enemy-enc_221",
			"DisplayName": "Enemy Placeholder",
			"UnitRole": "enemy",
			"Stats": {
				"MaxHP": 88,
				"CurrentHP": 0,
				"Attack": 11
			},
			"SkillIds": [],
			"PassiveSkillIds": [],
			"RelicIds": [],
			"BuffIds": [],
			"DebuffIds": ["debuff_exposed"]
		}
	}
	return {
		"GameId": "g1",
		"PlayerId": "p1",
		"EncounterId": "enc_221",
		"Result": {
			"Outcome": "win",
			"MoneyDelta": 12,
			"EncounterTarget": 11,
			"EffectiveCombatRating": 13,
			"PlayerSnapshot": snapshot_player,
			"EnemySnapshot": snapshot_enemy
		},
		"OccurredAt": "2026-01-01T00:00:01Z",
		"CorrelationId": "corr-221",
		"CausationId": "ui.sanguo.tile.action.selected",
		"PlayerSnapshot": snapshot_player,
		"EnemySnapshot": snapshot_enemy
	}

func _publish_started(payload: Dictionary) -> void:
	_bus.PublishSimple(EVENT_COMBAT_STARTED, "ut", JSON.stringify(payload))

func _publish_ended(payload: Dictionary) -> void:
	_bus.PublishSimple(EVENT_COMBAT_ENDED, "ut", JSON.stringify(payload))

func _started_text_for(payload: Dictionary) -> String:
	var view := await _battle_view()
	_publish_started(payload)
	await get_tree().process_frame
	return _details_text(view)

func _ended_text_and_continue_disabled(started_payload: Dictionary, ended_payload: Dictionary) -> Array:
	var view := await _battle_view()
	_publish_started(started_payload)
	await get_tree().process_frame
	_publish_ended(ended_payload)
	await get_tree().process_frame
	var continue_btn: Button = view.get_node("Panel/VBox/ContinueButton")
	return [_details_text(view), continue_btn.disabled]

# ACC:T221.1
func test_task221_combat_placeholder_surfaces_include_names_categories_and_empty_states() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Started (encounter=enc_221)")
	assert_str(started_text).contains("Player:")
	assert_str(started_text).contains("Enemy:")
	assert_str(started_text).not_contains("unavailable")

# ACC:T221.2
func test_task221_anchor_2_binding() -> void:
	var payload := _started_payload_with_placeholders()
	payload["EnemySnapshot"]["Summons"] = [
		{
			"UnitId": "enemy-additional",
			"DisplayName": "Enemy Additional",
			"UnitRole": "enemy",
			"Stats": {
				"MaxHP": 40,
				"CurrentHP": 35,
				"Attack": 6
			},
			"SkillIds": [],
			"PassiveSkillIds": [],
			"RelicIds": [],
			"BuffIds": [],
			"DebuffIds": []
		}
	]
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Player: Player Placeholder")
	assert_str(started_text).contains("Enemy: Enemy Placeholder,Enemy Additional")
	assert_str(started_text).contains("Enemy Additional")

# ACC:T221.3
func test_task221_anchor_3_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Player: Player Placeholder [player] | Model=p1-main")
	assert_str(started_text).contains("Enemy: Enemy Placeholder [enemy] | Model=enemy-enc_221")

# ACC:T221.4
func test_task221_anchor_4_binding() -> void:
	var payload := _started_payload_with_placeholders()
	payload["PlayerSnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 77
	payload["EnemySnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 66
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Runtime=HP 77/100, ATK 12")
	assert_str(started_text).contains("Runtime=HP 66/88, ATK 11")

	var ended_payload := _ended_payload_with_placeholders()
	ended_payload["Result"]["PlayerSnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 31
	ended_payload["Result"]["EnemySnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 9
	ended_payload["PlayerSnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 31
	ended_payload["EnemySnapshot"]["MainUnit"]["Stats"]["CurrentHP"] = 9
	var ended_result := await _ended_text_and_continue_disabled(payload, ended_payload)
	var ended_text := str(ended_result[0])

	assert_str(started_text).contains("Runtime=HP 77/100, ATK 12")
	assert_str(started_text).contains("Runtime=HP 66/88, ATK 11")
	assert_str(ended_text).contains("Runtime=HP 31/100, ATK 12")
	assert_str(ended_text).contains("Runtime=HP 9/88, ATK 11")

# ACC:T221.5
func test_task221_anchor_5_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Skills=skill_basic_strike")

# ACC:T221.6
func test_task221_anchor_6_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Passives=empty")

# ACC:T221.7
func test_task221_anchor_7_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Relics=empty")

# ACC:T221.8
func test_task221_anchor_8_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Buffs=buff_ready")
	assert_str(started_text).contains("Debuffs=debuff_exposed")

# ACC:T221.9
func test_task221_anchor_9_binding() -> void:
	var started_text := await _started_text_for(_started_payload_with_placeholders())
	assert_str(started_text).contains("Debuffs=empty")

# ACC:T221.10
func test_task221_anchor_10_binding() -> void:
	var result := await _ended_text_and_continue_disabled(
		_started_payload_with_placeholders(),
		_ended_payload_with_placeholders())
	assert_str(str(result[0])).contains("Result: win")

# ACC:T221.11
func test_task221_anchor_11_binding() -> void:
	var result := await _ended_text_and_continue_disabled(
		_started_payload_with_placeholders(),
		_ended_payload_with_placeholders())
	assert_bool(bool(result[1])).is_false()

# ACC:T221.12
func test_task221_anchor_12_binding() -> void:
	var payload := {
		"GameId": "g1",
		"PlayerId": "p1",
		"EncounterId": "enc_221",
		"RandomSeed": 7,
		"OccurredAt": "2026-01-01T00:00:00Z",
		"CorrelationId": "corr-221",
		"CausationId": "ui.sanguo.tile.action.selected"
	}
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Player: unavailable")
	assert_str(started_text).contains("Enemy: unavailable")

# ACC:T221.13
func test_task221_anchor_13_binding() -> void:
	var payload := {
		"GameId": "g1",
		"PlayerId": "p1",
		"EncounterId": "enc_221",
		"RandomSeed": 7,
		"OccurredAt": "2026-01-01T00:00:00Z",
		"CorrelationId": "corr-221",
		"CausationId": "ui.sanguo.tile.action.selected",
		"PlayerSnapshot": {
			"MainUnit": {
				"UnitId": "p1-main",
				"DisplayName": "Player Placeholder",
				"UnitRole": "player"
			}
		},
		"EnemySnapshot": {
			"MainUnit": {
				"UnitId": "enemy-enc_221",
				"DisplayName": "Enemy Placeholder",
				"UnitRole": "enemy"
			}
		}
	}
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Runtime=unavailable")

# ACC:T221.14
func test_task221_anchor_14_binding() -> void:
	var payload := {
		"GameId": "g1",
		"PlayerId": "p1",
		"EncounterId": "enc_221",
		"RandomSeed": 7,
		"OccurredAt": "2026-01-01T00:00:00Z",
		"CorrelationId": "corr-221",
		"CausationId": "ui.sanguo.tile.action.selected",
		"PlayerSnapshot": {
			"MainUnit": {
				"UnitId": "p1-main",
				"DisplayName": "Player Placeholder",
				"UnitRole": "player",
				"Stats": {
					"MaxHP": 100,
					"CurrentHP": 98,
					"Attack": 12
				}
			}
		},
		"EnemySnapshot": {
			"MainUnit": {
				"UnitId": "enemy-enc_221",
				"DisplayName": "Enemy Placeholder",
				"UnitRole": "enemy",
				"Stats": {
					"MaxHP": 88,
					"CurrentHP": 88,
					"Attack": 11
				}
			}
		}
	}
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Skills=unavailable")
	assert_str(started_text).contains("Passives=unavailable")
	assert_str(started_text).contains("Relics=unavailable")
	assert_str(started_text).contains("Buffs=unavailable")
	assert_str(started_text).contains("Debuffs=unavailable")

# ACC:T221.15
func test_task221_anchor_15_binding() -> void:
	var payload := _started_payload_with_placeholders()
	payload["PlayerSnapshot"]["MainUnit"]["SkillIds"] = []
	payload["EnemySnapshot"]["MainUnit"]["SkillIds"] = []
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Skills=empty")

# ACC:T221.16
func test_task221_anchor_16_binding() -> void:
	var payload := _started_payload_with_placeholders()
	payload["PlayerSnapshot"] = {"Other": {}}
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Player: unavailable")
	assert_str(started_text).contains("Enemy: Enemy Placeholder")

# ACC:T221.17
func test_task221_anchor_17_binding() -> void:
	var view := await _battle_view()
	var started_payload := _started_payload_with_placeholders()
	var ended_payload := _ended_payload_with_placeholders()
	ended_payload["CorrelationId"] = "corr-221-mismatch"
	_publish_started(started_payload)
	await get_tree().process_frame
	var before_text := _details_text(view)
	_publish_ended(ended_payload)
	await get_tree().process_frame
	var after_text := _details_text(view)
	var continue_btn: Button = view.get_node("Panel/VBox/ContinueButton")
	assert_str(after_text).is_equal(before_text)
	assert_bool(continue_btn.disabled).is_true()

func test_task221_enemy_snapshot_missing_shows_unavailable() -> void:
	var payload := _started_payload_with_placeholders()
	payload.erase("EnemySnapshot")
	var started_text := await _started_text_for(payload)
	assert_str(started_text).contains("Player: Player Placeholder")
	assert_str(started_text).contains("Enemy: unavailable")
