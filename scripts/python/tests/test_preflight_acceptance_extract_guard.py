from __future__ import annotations

from scripts.python.preflight_acceptance_extract_guard import evaluate_task


def _build_master_task() -> dict[str, object]:
    return {
        "id": "181",
        "title": "Add test coverage for v4 assertions part 1 enemy boss main unit combat",
        "description": "# PRD V4 Acceptance Assertions (Combat)",
        "details": "Acceptance: Requirement REQ-1 is implemented with traceable evidence.",
        "testStrategy": "Run deterministic validator.",
    }


def test_single_present_view_does_not_fail_missing_acceptance_view() -> None:
    master = _build_master_task()
    back = {
        "taskmaster_id": 181,
        "acceptance": [
            "Requirement REQ-1 is implemented with traceable evidence. Refs: Tests.Godot/tests/sample.gd",
        ],
    }

    payload = evaluate_task(task_id="181", master=master, back=back, gameplay=None)

    assert payload["status"] == "ok"
    assert "missing_acceptance_view" not in payload["issue_ids"]


def test_both_present_views_require_acceptance_on_each_side() -> None:
    master = _build_master_task()
    back = {
        "taskmaster_id": 181,
        "acceptance": [
            "Requirement REQ-1 is implemented with traceable evidence. Refs: Tests.Godot/tests/sample.gd",
        ],
    }
    gameplay = {
        "taskmaster_id": 181,
        "acceptance": [
            "Requirement REQ-2 is implemented with traceable evidence. Refs: Tests.Godot/tests/sample_2.gd",
        ],
    }

    payload = evaluate_task(task_id="181", master=master, back=back, gameplay=gameplay)

    assert payload["status"] == "ok"
    assert "missing_acceptance_view" not in payload["issue_ids"]
