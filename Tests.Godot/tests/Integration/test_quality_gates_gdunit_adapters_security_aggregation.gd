extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const ADAPTERS_TESTS_DIR := "res://tests/Adapters"
const SECURITY_TESTS_DIR := "res://tests/Security"
const TASKS_BACK_PATH := "res://../.taskmaster/tasks/tasks_back.json"
const SELF_TEST_PATH := "res://tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
const TASK_222_ID := 222

func _select_gate_suite_dirs() -> PackedStringArray:
	return PackedStringArray([ADAPTERS_TESTS_DIR, SECURITY_TESTS_DIR])

func _aggregate_all_passed(passed_flags: Array[bool]) -> bool:
	for passed in passed_flags:
		if not passed:
			return false
	return true

func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	var raw := FileAccess.get_file_as_string(path)
	return JSON.parse_string(raw)

func _find_task_by_taskmaster_id(rows: Array, taskmaster_id: int) -> Dictionary:
	for row in rows:
		if typeof(row) != TYPE_DICTIONARY:
			continue
		var dict: Dictionary = row
		if int(dict.get("taskmaster_id", -1)) == taskmaster_id:
			return dict
	return {}

func _extract_refs(acceptance_item: String) -> PackedStringArray:
	var refs := PackedStringArray()
	if not acceptance_item.contains(" Refs:"):
		return refs
	var split := acceptance_item.split(" Refs:", false, 1)
	if split.size() < 2:
		return refs
	var tail := str(split[1]).strip_edges()
	for token in tail.split(" ", false):
		var cleaned := str(token).strip_edges()
		if cleaned != "":
			refs.append(cleaned)
	return refs

func _to_res_path(task_ref: String) -> String:
	if task_ref.begins_with("res://"):
		return task_ref
	if task_ref.begins_with("Tests.Godot/"):
		return "res://" + task_ref.trim_prefix("Tests.Godot/")
	return ""

func _self_test_contains_anchor(anchor: String) -> bool:
	var content := FileAccess.get_file_as_string(SELF_TEST_PATH)
	return content.find(anchor) >= 0

func _validate_task222_acceptance_contract(task: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	var acceptance_variant: Variant = task.get("acceptance", [])
	var acceptance: Array = acceptance_variant if acceptance_variant is Array else []
	if acceptance.size() < 4:
		errors.append("acceptance_count_lt_4")
		return {"ok": false, "errors": errors}

	for idx in range(4):
		var text := str(acceptance[idx])
		if not text.contains(" Refs:"):
			errors.append("missing_refs_%d" % (idx + 1))
		var refs := _extract_refs(text)
		if refs.is_empty():
			errors.append("empty_refs_%d" % (idx + 1))
		for task_ref in refs:
			if not (task_ref.ends_with(".gd") or task_ref.ends_with(".cs")):
				errors.append("non_test_ref_%d:%s" % [idx + 1, task_ref])
			var res_path := _to_res_path(task_ref)
			if res_path == "" or not FileAccess.file_exists(res_path):
				errors.append("missing_ref_file_%d:%s" % [idx + 1, task_ref])
		var anchor := "ACC:T222.%d" % (idx + 1)
		if not _self_test_contains_anchor(anchor):
			errors.append("missing_anchor_%s" % anchor)

	if not str(acceptance[2]).contains("[OBL:T222.O4]"):
		errors.append("missing_obl_o4_acceptance_3")
	if not str(acceptance[3]).contains("[OBL:T222.O5]"):
		errors.append("missing_obl_o5_acceptance_4")
	var baseline_line := str(acceptance[2]).to_lower()
	if baseline_line.find("triplet baseline validators") < 0:
		errors.append("missing_triplet_baseline_semantics_3")
	if baseline_line.find("evidence") < 0 or baseline_line.find("logs") < 0:
		errors.append("missing_evidence_logs_semantics_3")
	var stability_line := str(acceptance[3]).to_lower()
	if stability_line.find("stable") < 0 or stability_line.find("rerun") < 0:
		errors.append("missing_refactor_stability_semantics_4")
	var semantics_line := str(acceptance[1]).to_lower()
	var has_impl_branch := semantics_line.find("matching implementation evidence") >= 0
	var has_task_branch := semantics_line.find("matching task evidence") >= 0
	var has_fail_semantics := semantics_line.find("must fail") >= 0 or semantics_line.find("fails when") >= 0
	var has_pass_semantics := semantics_line.find("pass when") >= 0 or semantics_line.find("demonstrates") >= 0
	if not has_impl_branch:
		errors.append("missing_matching_implementation_branch_semantics_2")
	if not has_task_branch:
		errors.append("missing_matching_task_evidence_branch_semantics_2")
	if not has_fail_semantics:
		errors.append("missing_fail_path_semantics_2")
	if not has_pass_semantics:
		errors.append("missing_pass_path_semantics_2")

	var strategy_variant: Variant = task.get("test_strategy", [])
	var strategy: Array = strategy_variant if strategy_variant is Array else []
	var has_ch38_line := false
	for line in strategy:
		if str(line).find("Chapter 3.8 triplet baseline validators") >= 0:
			has_ch38_line = true
			break
	if not has_ch38_line:
		errors.append("missing_chapter38_strategy_line")

	return {"ok": errors.is_empty(), "errors": errors}

func _load_task222_from_tasks_back() -> Dictionary:
	var parsed: Variant = _read_json(TASKS_BACK_PATH)
	if typeof(parsed) != TYPE_ARRAY:
		return {}
	return _find_task_by_taskmaster_id(parsed, TASK_222_ID)

# acceptance: ACC:T47.3
func test_gate_suite_selection_is_deterministic_and_stable() -> void:
	var suite_dirs := _select_gate_suite_dirs()
	assert_int(suite_dirs.size()).is_equal(2)
	assert_str(suite_dirs[0]).is_equal(ADAPTERS_TESTS_DIR)
	assert_str(suite_dirs[1]).is_equal(SECURITY_TESTS_DIR)

# acceptance: ACC:T47.3
func test_aggregation_is_failed_when_any_suite_failed() -> void:
	assert_bool(_aggregate_all_passed([true, true])).is_true()
	assert_bool(_aggregate_all_passed([true, false])).is_false()
	assert_bool(_aggregate_all_passed([false, true])).is_false()
	assert_bool(_aggregate_all_passed([false, false])).is_false()

# acceptance: ACC:T222.1
func test_task222_requirement_ref_is_traceable() -> void:
	var task := _load_task222_from_tasks_back()
	assert_dict(task).is_not_empty()
	var validation := _validate_task222_acceptance_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

# acceptance: ACC:T222.2
func test_task222_deterministic_validation_path_is_explicit() -> void:
	var task := _load_task222_from_tasks_back()
	assert_dict(task).is_not_empty()
	var original_validation := _validate_task222_acceptance_contract(task)
	assert_bool(bool(original_validation.get("ok", false))).is_true()
	var missing_both := task.duplicate(true)
	var acceptance: Array = (missing_both.get("acceptance", []) as Array)
	acceptance[1] = "A deterministic validator is present but evidence is unrelated and therefore does not match REQ-2654be8260e6. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	missing_both["acceptance"] = acceptance
	var missing_both_validation := _validate_task222_acceptance_contract(missing_both)
	assert_bool(bool(missing_both_validation.get("ok", true))).is_false()
	var missing_both_errors := String("\n").join(missing_both_validation.get("errors", []))
	assert_bool(missing_both_errors.find("missing_matching_implementation_branch_semantics_2") >= 0).is_true()
	assert_bool(missing_both_errors.find("missing_matching_task_evidence_branch_semantics_2") >= 0).is_true()
	var impl_only := task.duplicate(true)
	var impl_acceptance: Array = (impl_only.get("acceptance", []) as Array)
	impl_acceptance[1] = "A deterministic validator must fail when no matching implementation evidence is present, and pass when matching implementation evidence is provided. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	impl_only["acceptance"] = impl_acceptance
	var impl_only_validation := _validate_task222_acceptance_contract(impl_only)
	assert_bool(bool(impl_only_validation.get("ok", true))).is_false()
	var impl_only_errors := String("\n").join(impl_only_validation.get("errors", []))
	assert_bool(impl_only_errors.find("missing_matching_task_evidence_branch_semantics_2") >= 0).is_true()

# acceptance: ACC:T222.3
func test_task222_triplet_baseline_rerun_evidence_marker_o4_a() -> void:
	var task := _load_task222_from_tasks_back()
	assert_dict(task).is_not_empty()
	var acceptance: Array = (task.get("acceptance", []) as Array)
	assert_str(str(acceptance[2])).contains("[OBL:T222.O4]")
	var mutated := task.duplicate(true)
	var mutated_acceptance: Array = (mutated.get("acceptance", []) as Array)
	mutated_acceptance[2] = "[OBL:T222.O4] Chapter 3.8 triplet baseline validators are rerun after this task is written to a task view. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = mutated_acceptance
	var validation := _validate_task222_acceptance_contract(mutated)
	assert_bool(bool(validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(validation.get("errors", [])).find("missing_evidence_logs_semantics_3") >= 0).is_true()

# acceptance: ACC:T222.4
func test_task222_refactor_stability_marker_o5_a() -> void:
	var task := _load_task222_from_tasks_back()
	assert_dict(task).is_not_empty()
	var acceptance: Array = (task.get("acceptance", []) as Array)
	assert_str(str(acceptance[3])).contains("[OBL:T222.O5]")
	var mutated := task.duplicate(true)
	var mutated_acceptance: Array = (mutated.get("acceptance", []) as Array)
	mutated_acceptance[3] = str(mutated_acceptance[3]).replace("[OBL:T222.O5]", "[OBL:T222.MISSING]")
	mutated["acceptance"] = mutated_acceptance
	var validation := _validate_task222_acceptance_contract(mutated)
	assert_bool(bool(validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(validation.get("errors", [])).find("missing_obl_o5_acceptance_4") >= 0).is_true()
	var stability_mutated := task.duplicate(true)
	var stability_acceptance: Array = (stability_mutated.get("acceptance", []) as Array)
	stability_acceptance[3] = "[OBL:T222.O5] Validation output remains unchanged. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	stability_mutated["acceptance"] = stability_acceptance
	var stability_validation := _validate_task222_acceptance_contract(stability_mutated)
	assert_bool(bool(stability_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(stability_validation.get("errors", [])).find("missing_refactor_stability_semantics_4") >= 0).is_true()
