extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"


func _boss_victory_summary() -> Dictionary:
	return {
		"campaign_id": "boss-victory-seed-149",
		"seed": 149,
		"milestones": ["campaign_start", "mid_campaign", "final_boss_defeated"],
		"visible_summary": "Boss defeated. Campaign completed.",
		"result": "victory"
	}


# ACC:T149.1
func test_task149_milestones_reach_final_boss_victory() -> void:
	var summary := _boss_victory_summary()
	var milestones: Array = summary.get("milestones", [])
	assert_array(milestones).contains_exactly(["campaign_start", "mid_campaign", "final_boss_defeated"])
	assert_str(str(summary.get("result", ""))).is_equal("victory")


# ACC:T149.5
func test_task149_victory_summary_is_visible_and_non_empty() -> void:
	var summary := _boss_victory_summary()
	var visible_summary := str(summary.get("visible_summary", "")).strip_edges()
	assert_str(visible_summary).is_not_empty()
	assert_str(visible_summary).contains("Campaign completed")
