extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

const ADAPTERS_TESTS_DIR := "res://tests/Adapters"
const SECURITY_TESTS_DIR := "res://tests/Security"
const TASKS_BACK_PATH := "res://../.taskmaster/tasks/tasks_back.json"
const TASKS_GAMEPLAY_PATH := "res://../.taskmaster/tasks/tasks_gameplay.json"
const SELF_TEST_PATH := "res://tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
const TASK_190_ID := 190
const TASK_191_ID := 191
const TASK_192_ID := 192
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

func _load_task190_from_tasks_gameplay() -> Dictionary:
	var parsed: Variant = _read_json(TASKS_GAMEPLAY_PATH)
	if typeof(parsed) != TYPE_ARRAY:
		return {}
	return _find_task_by_taskmaster_id(parsed, TASK_190_ID)

func _load_task191_from_tasks_gameplay() -> Dictionary:
	var parsed: Variant = _read_json(TASKS_GAMEPLAY_PATH)
	if typeof(parsed) != TYPE_ARRAY:
		return {}
	return _find_task_by_taskmaster_id(parsed, TASK_191_ID)

func _load_task192_from_tasks_gameplay() -> Dictionary:
	var parsed: Variant = _read_json(TASKS_GAMEPLAY_PATH)
	if typeof(parsed) != TYPE_ARRAY:
		return {}
	return _find_task_by_taskmaster_id(parsed, TASK_192_ID)

func _validate_task190_chapter3_evidence_contract(task: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	var acceptance_variant: Variant = task.get("acceptance", [])
	var acceptance: Array = acceptance_variant if acceptance_variant is Array else []
	if acceptance.size() < 11:
		errors.append("acceptance_count_lt_11")
		return {"ok": false, "errors": errors}

	var evidence_ref := "Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	var o10 := str(acceptance[9])
	var o11 := str(acceptance[10])
	if not o10.contains("[OBL:T190.O10]"):
		errors.append("missing_obl_o10_acceptance_10")
	if not o11.contains("[OBL:T190.O11]"):
		errors.append("missing_obl_o11_acceptance_11")
	if not o10.contains("Chapter 3 coverage audit") or not o10.to_lower().contains("evidence recorded"):
		errors.append("missing_coverage_audit_evidence_semantics_10")
	if not o11.contains("Chapter 3.8 triplet baseline validators") or not o11.to_lower().contains("evidence"):
		errors.append("missing_triplet_validator_evidence_semantics_11")
	for idx in [9, 10]:
		var refs := _extract_refs(str(acceptance[idx]))
		if refs.size() != 1 or refs[0] != evidence_ref:
			errors.append("wrong_chapter3_evidence_ref_%d" % (idx + 1))
		var res_path := _to_res_path(evidence_ref)
		if res_path == "" or not FileAccess.file_exists(res_path):
			errors.append("missing_evidence_ref_file_%d" % (idx + 1))

	var refs_variant: Variant = task.get("test_refs", [])
	var refs: Array = refs_variant if refs_variant is Array else []
	if not refs.has(evidence_ref):
		errors.append("missing_evidence_ref_in_test_refs")
	if not _self_test_contains_anchor("ACC:T190.10"):
		errors.append("missing_anchor_ACC:T190.10")
	if not _self_test_contains_anchor("ACC:T190.11"):
		errors.append("missing_anchor_ACC:T190.11")

	var strategy_variant: Variant = task.get("test_strategy", [])
	var strategy: Array = strategy_variant if strategy_variant is Array else []
	var has_coverage_audit := false
	var has_triplet_validators := false
	for line in strategy:
		var text := str(line)
		if text.find("Chapter 3 coverage audit") >= 0:
			has_coverage_audit = true
		if text.find("Chapter 3.8 triplet baseline validators") >= 0:
			has_triplet_validators = true
	if not has_coverage_audit:
		errors.append("missing_chapter3_coverage_strategy_line")
	if not has_triplet_validators:
		errors.append("missing_chapter38_strategy_line")

	return {"ok": errors.is_empty(), "errors": errors}

func _validate_task191_unwired_candidate_contract(task: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	var acceptance_variant: Variant = task.get("acceptance", [])
	var acceptance: Array = acceptance_variant if acceptance_variant is Array else []
	if acceptance.size() < 16:
		errors.append("acceptance_count_lt_16")
		return {"ok": false, "errors": errors}

	var evidence_ref := "Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	var expected_requirements := {
		"REQ-eae21fdbb220": "docs/gdd/ui-gdd-flow.md:377",
		"REQ-83aa374c2f2a": "docs/gdd/ui-gdd-flow.md:386",
		"REQ-b06e000b15c4": "docs/gdd/ui-gdd-flow.md:393",
		"REQ-dc30e0f48bde": "docs/gdd/ui-gdd-flow.md:400",
	}

	for idx in range(16):
		var text := str(acceptance[idx])
		var refs := _extract_refs(text)
		if idx == 9:
			if not refs.has(evidence_ref) or not refs.has("Game.Core.Tests/Utilities/NoGodotDependencyTests.cs"):
				errors.append("wrong_task191_core_boundary_refs_%d" % (idx + 1))
		elif refs.size() != 1 or refs[0] != evidence_ref:
			errors.append("wrong_task191_evidence_ref_%d" % (idx + 1))
		var res_path := _to_res_path(evidence_ref)
		if res_path == "" or not FileAccess.file_exists(res_path):
			errors.append("missing_task191_evidence_ref_file_%d" % (idx + 1))
		var anchor := "ACC:T191.%d" % (idx + 1)
		if not _self_test_contains_anchor(anchor):
			errors.append("missing_anchor_%s" % anchor)

	var requirement_ids_variant: Variant = task.get("requirement_ids", [])
	var requirement_ids: Array = requirement_ids_variant if requirement_ids_variant is Array else []
	for requirement_id in expected_requirements.keys():
		if not requirement_ids.has(requirement_id):
			errors.append("missing_requirement_id_%s" % requirement_id)

	for idx in range(4):
		var text := str(acceptance[idx])
		var requirement_id := str(expected_requirements.keys()[idx])
		if not text.contains(requirement_id):
			errors.append("missing_requirement_%d:%s" % [idx + 1, requirement_id])
		if not text.contains(str(expected_requirements[requirement_id])):
			errors.append("missing_source_line_%d:%s" % [idx + 1, requirement_id])

	var visible_line := str(acceptance[10]).to_lower()
	for requirement_id in expected_requirements.keys():
		if visible_line.find(str(requirement_id).to_lower()) < 0:
			errors.append("visible_list_missing_%s" % requirement_id)
	if visible_line.find("source line identity") < 0:
		errors.append("visible_list_missing_source_identity_semantics")

	var partial_line := str(acceptance[11]).to_lower()
	if partial_line.find("still not wired") < 0 or partial_line.find("unwired") < 0:
		errors.append("missing_partial_unwired_semantics_12")
	var complete_line := str(acceptance[12]).to_lower()
	if complete_line.find("all four") < 0 or complete_line.find("no remaining") < 0:
		errors.append("missing_all_wired_empty_semantics_13")
	var unrelated_line := str(acceptance[13]).to_lower()
	if unrelated_line.find("unrelated ui requirements") < 0 or unrelated_line.find("does not mark") < 0:
		errors.append("missing_unrelated_requirement_negative_semantics_14")

	var o8 := str(acceptance[14])
	var o9 := str(acceptance[15])
	if not o8.contains("[OBL:T191.O8]"):
		errors.append("missing_obl_o8_acceptance_15")
	if not o9.contains("[OBL:T191.O9]"):
		errors.append("missing_obl_o9_acceptance_16")
	for requirement_id in expected_requirements.keys():
		if not o8.contains(requirement_id):
			errors.append("o8_missing_requirement_%s" % requirement_id)
		if not o9.contains(requirement_id):
			errors.append("o9_missing_requirement_%s" % requirement_id)

	var refs_variant: Variant = task.get("test_refs", [])
	var refs: Array = refs_variant if refs_variant is Array else []
	if refs.size() != 2:
		errors.append("task191_test_refs_count_not_2")
	if not refs.has(evidence_ref):
		errors.append("missing_task191_evidence_ref_in_test_refs")
	if not refs.has("Game.Core.Tests/Utilities/NoGodotDependencyTests.cs"):
		errors.append("missing_task191_core_boundary_ref_in_test_refs")

	return {"ok": errors.is_empty(), "errors": errors}

func _validate_task192_process_evidence_contract(task: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	var acceptance_variant: Variant = task.get("acceptance", [])
	var acceptance: Array = acceptance_variant if acceptance_variant is Array else []
	if acceptance.size() < 15:
		errors.append("acceptance_count_lt_15")
		return {"ok": false, "errors": errors}

	var evidence_ref := "Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	var expected_requirements := [
		"REQ-5187ab7a9fc0",
		"REQ-f2066975f93c",
		"REQ-61e0a6902857",
		"REQ-71589cb62f34",
	]
	for idx in [11, 12, 13, 14]:
		var refs := _extract_refs(str(acceptance[idx]))
		if refs.size() != 1 or refs[0] != evidence_ref:
			errors.append("wrong_task192_process_ref_%d" % (idx + 1))
		var res_path := _to_res_path(evidence_ref)
		if res_path == "" or not FileAccess.file_exists(res_path):
			errors.append("missing_task192_process_ref_file_%d" % (idx + 1))
		var anchor := "ACC:T192.%d" % (idx + 1)
		if not _self_test_contains_anchor(anchor):
			errors.append("missing_anchor_%s" % anchor)

	var o8_a := str(acceptance[11])
	var o8_b := str(acceptance[12])
	var o9_a := str(acceptance[13])
	var o9_b := str(acceptance[14])
	if not o8_a.contains("[OBL:T192.O8]") or not o8_b.contains("[OBL:T192.O8]"):
		errors.append("missing_obl_o8_acceptance")
	if not o9_a.contains("[OBL:T192.O9]") or not o9_b.contains("[OBL:T192.O9]"):
		errors.append("missing_obl_o9_acceptance")
	var o8_a_lower := o8_a.to_lower()
	var o9_a_lower := o9_a.to_lower()
	if o8_a.find("Chapter 3 coverage audit") < 0 or o8_a_lower.find("evidence") < 0 or (o8_a_lower.find("evidence path") < 0 and o8_a_lower.find("evidence recorded") < 0):
		errors.append("missing_coverage_audit_evidence_semantics_12")
	if o9_a.find("Chapter 3.8 triplet baseline validators") < 0 or o9_a_lower.find("evidence") < 0 or (o9_a_lower.find("evidence path") < 0 and o9_a_lower.find("evidence recorded") < 0):
		errors.append("missing_triplet_validator_evidence_semantics_14")
	for requirement_id in expected_requirements:
		var seen := false
		for line in acceptance:
			if str(line).contains(requirement_id):
				seen = true
				break
		if not seen:
			errors.append("missing_requirement_%s" % requirement_id)

	var refs_variant: Variant = task.get("test_refs", [])
	var refs: Array = refs_variant if refs_variant is Array else []
	if not refs.has(evidence_ref):
		errors.append("missing_task192_process_ref_in_test_refs")

	return {"ok": errors.is_empty(), "errors": errors}

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

# acceptance: ACC:T190.10
func test_task190_chapter3_coverage_audit_evidence_is_task_bound() -> void:
	var task := _load_task190_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var validation := _validate_task190_chapter3_evidence_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

	var mutated := task.duplicate(true)
	var acceptance: Array = (mutated.get("acceptance", []) as Array)
	acceptance[9] = "[OBL:T190.O10] Refactor preserves deterministic core boundaries only. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = acceptance
	var mutated_validation := _validate_task190_chapter3_evidence_contract(mutated)
	assert_bool(bool(mutated_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(mutated_validation.get("errors", [])).find("missing_coverage_audit_evidence_semantics_10") >= 0).is_true()

# acceptance: ACC:T190.11
func test_task190_chapter38_triplet_validator_evidence_is_task_bound() -> void:
	var task := _load_task190_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var validation := _validate_task190_chapter3_evidence_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

	var mutated := task.duplicate(true)
	var acceptance: Array = (mutated.get("acceptance", []) as Array)
	acceptance[10] = "[OBL:T190.O11] After this task is written to a task view, the validator note is present but no evidence is recorded. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = acceptance
	var mutated_validation := _validate_task190_chapter3_evidence_contract(mutated)
	assert_bool(bool(mutated_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(mutated_validation.get("errors", [])).find("missing_triplet_validator_evidence_semantics_11") >= 0).is_true()

func _assert_task191_unwired_candidate_contract_is_valid() -> void:
	var task := _load_task191_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var validation := _validate_task191_unwired_candidate_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

# acceptance: ACC:T191.1
# acceptance: ACC:T191.2
# acceptance: ACC:T191.3
# acceptance: ACC:T191.4
func test_task191_requirement_source_evidence_is_task_bound() -> void:
	_assert_task191_unwired_candidate_contract_is_valid()

# acceptance: ACC:T191.5
# acceptance: ACC:T191.6
# acceptance: ACC:T191.7
# acceptance: ACC:T191.8
# acceptance: ACC:T191.9
func test_task191_candidate_feature_evidence_is_task_bound() -> void:
	_assert_task191_unwired_candidate_contract_is_valid()

# acceptance: ACC:T191.10
# acceptance: ACC:T191.11
# acceptance: ACC:T191.12
# acceptance: ACC:T191.13
# acceptance: ACC:T191.14
func test_task191_wired_unwired_state_evidence_is_task_bound() -> void:
	_assert_task191_unwired_candidate_contract_is_valid()

# acceptance: ACC:T191.15
# acceptance: ACC:T191.16
func test_task191_chapter3_process_evidence_is_task_bound() -> void:
	_assert_task191_unwired_candidate_contract_is_valid()

# acceptance: ACC:T191.12
func test_task191_partial_unwired_evidence_rejects_generic_adapter_claims() -> void:
	var task := _load_task191_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var mutated := task.duplicate(true)
	var mutated_acceptance: Array = (mutated.get("acceptance", []) as Array)
	mutated_acceptance[11] = "When any of the four listed UI requirements is still not wired, generic adapter evidence is present. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = mutated_acceptance
	var mutated_validation := _validate_task191_unwired_candidate_contract(mutated)
	assert_bool(bool(mutated_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(mutated_validation.get("errors", [])).find("missing_partial_unwired_semantics_12") >= 0).is_true()

# acceptance: ACC:T192.12
# acceptance: ACC:T192.13
func test_task192_chapter3_coverage_audit_evidence_is_task_bound() -> void:
	var task := _load_task192_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var validation := _validate_task192_process_evidence_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

	var mutated := task.duplicate(true)
	var acceptance: Array = (mutated.get("acceptance", []) as Array)
	acceptance[11] = "[OBL:T192.O8] Chapter 3 coverage audit is mentioned without evidence. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = acceptance
	var mutated_validation := _validate_task192_process_evidence_contract(mutated)
	assert_bool(bool(mutated_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(mutated_validation.get("errors", [])).find("missing_coverage_audit_evidence_semantics_12") >= 0).is_true()

# acceptance: ACC:T192.14
# acceptance: ACC:T192.15
func test_task192_chapter38_triplet_validator_evidence_is_task_bound() -> void:
	var task := _load_task192_from_tasks_gameplay()
	assert_dict(task).is_not_empty()
	var validation := _validate_task192_process_evidence_contract(task)
	assert_bool(bool(validation.get("ok", false))).is_true()

	var mutated := task.duplicate(true)
	var acceptance: Array = (mutated.get("acceptance", []) as Array)
	acceptance[13] = "[OBL:T192.O9] Chapter 3.8 triplet baseline validators are mentioned without evidence. Refs: Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd"
	mutated["acceptance"] = acceptance
	var mutated_validation := _validate_task192_process_evidence_contract(mutated)
	assert_bool(bool(mutated_validation.get("ok", true))).is_false()
	assert_bool(String("\n").join(mutated_validation.get("errors", [])).find("missing_triplet_validator_evidence_semantics_14") >= 0).is_true()
