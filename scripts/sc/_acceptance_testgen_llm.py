from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Model output is empty.")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE):
        chunk = (match.group(1) or "").strip()
        if not chunk:
            continue
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[index:])
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("No JSON object found in model output.")


def build_prompt_for_ref(
    *,
    task_id: str,
    title: str,
    ref: str,
    acceptance_texts: list[str],
    required_anchors: list[str],
    intent: str,
    task_context_markdown: str,
    testing_framework_excerpt: str,
    truncate_fn: Callable[[str, int], str],
) -> str:
    ext = Path(ref).suffix.lower()
    if ext == ".gd":
        base_rules = [
            "Target file type: GDScript (GdUnit4 test suite).",
            "- Must be valid .gd, English only.",
            "- Must extend a GdUnit4 suite (res://addons/gdUnit4/src/GdUnitTestSuite.gd).",
            "- File name must use test_<behavior>.gd naming.",
            "- Test functions must use test_<behavior> naming.",
            "- Do not rely on external assets; keep it minimal.",
            "- For each required ACC anchor, place it within 5 lines ABOVE a `func test_...` definition (as a comment).",
        ]
    else:
        base_rules = [
            "Target file type: C# xUnit test file.",
            "- Must be valid C# code, English only (no Chinese in code/comments/strings).",
            "- Use xUnit + FluentAssertions only.",
            "- File name must be PascalCase and end with Tests.cs.",
            "- Class name must be PascalCase and match the file name stem.",
            "- Test method names must use exact ShouldX_WhenY style.",
            "- Local variable names must use camelCase.",
            "- For each required ACC anchor, place it within 5 lines ABOVE a [Fact]/[Theory] attribute (as a comment).",
        ]

    if intent == "red":
        intent_rules = [
            "TDD intent: RED-FIRST.",
            "- Must include at least one deterministic failing test aligned to acceptance intent.",
            "- Do NOT use trivial failures like assert_true(false) or throwing unconditionally.",
            "- Prefer a behavior failure (state/result/event ordering) over a pure 'type exists' failure.",
            "- If acceptance includes a 'must not / refuse / unchanged' clause, include a negative-path test for it.",
        ]
    else:
        intent_rules = [
            "Intent: SCAFFOLD.",
            "- Should NOT intentionally fail.",
            "- Prefer compile-safe smoke checks (e.g., type existence, contract constants, deterministic pure functions).",
            "- Include at least one real assertion that is likely to remain stable as implementation evolves.",
        ]

    constraints = "\n".join(
        [
            "Hard constraints:",
            "- Output MUST be valid JSON only (no Markdown).",
            "- JSON schema: {\"file_path\": \"<repo-relative>\", \"content\": \"<file content>\"}.",
            f"- file_path MUST be exactly: {ref}",
            "- Do NOT create any other files.",
            "- The generated file MUST include the required ACC anchors listed below.",
            *base_rules,
            *intent_rules,
        ]
    )

    acceptance_blob = truncate_fn("\n".join([f"- {text}" for text in acceptance_texts[:10]]), 6_000)
    anchors_blob = truncate_fn("\n".join([f"- {anchor}" for anchor in required_anchors]), 2_000)
    task_context = truncate_fn(task_context_markdown or "", 12_000)
    testing_excerpt = truncate_fn(testing_framework_excerpt or "", 10_000)

    instruction = "\n".join(
        [
            f"Task id: {task_id}",
            f"Task title: {title}",
            "",
            "Task context (from scripts/sc/analyze.py):",
            task_context or "(missing)",
            "",
            "Repository testing conventions excerpt (docs/testing-framework.md):",
            testing_excerpt or "(missing)",
            "",
            "Required ACC anchors to include in this file (each must be bound near a test marker):",
            anchors_blob or "(none)",
            "",
            "Acceptance items referencing this file:",
            acceptance_blob or "(none)",
            "",
            "Generate test content aligned to the acceptance intent and anchor requirements.",
        ]
    )
    return "\n\n".join([constraints, instruction]).strip() + "\n"


def build_select_primary_ref_prompt(
    *,
    task_id: str,
    title: str,
    candidates: list[dict[str, Any]],
    context_excerpt: str,
) -> str:
    constraints = "\n".join(
        [
            "You are selecting a single primary acceptance ref to drive a RED-FIRST test.",
            "",
            "Output constraints:",
            "- Output MUST be a single JSON object, no markdown.",
            "- Keys: primary_ref (string), reason (string).",
            "- primary_ref MUST be one of the provided candidate refs.",
            "",
            "Selection rules (in priority order):",
            "- Prefer C# (.cs) refs over .gd when both exist, because the TDD green/refactor workflow runs faster in .NET.",
            "- Prefer refs tied to concrete behavior (events/state transitions/calculations) over meta/process items.",
            "- Prefer smaller scope (one behavior) over broad integration tests.",
        ]
    )
    return "\n\n".join(
        [
            constraints,
            f"Task: {task_id}",
            f"Title: {title}",
            "",
            "Optional design context excerpt (truncated):",
            context_excerpt or "(disabled)",
            "",
            "Candidates (each includes acceptance texts that reference it):",
            json.dumps(candidates, ensure_ascii=False, indent=2),
            "",
            "Return JSON now.",
        ]
    ).strip() + "\n"


def select_primary_ref_with_llm(
    *,
    task_id: str,
    title: str,
    by_ref: dict[str, list[str]],
    context_excerpt: str,
    timeout_sec: int,
    out_dir: Path,
    is_allowed_test_path_fn: Callable[[str], bool],
    build_prompt_fn: Callable[..., str],
    run_codex_exec_fn: Callable[..., tuple[int, str, list[str]]],
    read_text_fn: Callable[[Path], str],
    write_text_fn: Callable[[Path, str], None],
) -> tuple[str | None, dict[str, Any]]:
    cs_refs = [ref for ref in sorted(by_ref.keys()) if ref.endswith(".cs") and is_allowed_test_path_fn(ref)]
    gd_refs = [ref for ref in sorted(by_ref.keys()) if ref.endswith(".gd") and is_allowed_test_path_fn(ref)]
    candidates = cs_refs if cs_refs else gd_refs
    if not candidates:
        return None, {"status": "skipped", "reason": "no_candidates"}

    payload = [{"ref": ref, "acceptance_texts": by_ref.get(ref, [])[:8]} for ref in candidates[:20]]
    prompt = build_prompt_fn(
        task_id=task_id,
        title=title,
        candidates=payload,
        context_excerpt=context_excerpt,
    )

    prompt_path = out_dir / f"primary-select-prompt-{task_id}.txt"
    last_msg_path = out_dir / f"primary-select-last-{task_id}.txt"
    trace_path = out_dir / f"primary-select-trace-{task_id}.log"
    write_text_fn(prompt_path, prompt)

    rc, trace_out, cmd = run_codex_exec_fn(prompt=prompt, out_last_message=last_msg_path, timeout_sec=timeout_sec)
    write_text_fn(trace_path, trace_out)
    last_msg = read_text_fn(last_msg_path) if last_msg_path.exists() else ""

    meta: dict[str, Any] = {
        "rc": rc,
        "cmd": cmd,
        "prompt_path": str(prompt_path),
        "trace_path": str(trace_path),
        "output_path": str(last_msg_path),
        "candidates": candidates,
    }

    if rc != 0 or not last_msg.strip():
        meta["status"] = "fail"
        meta["error"] = "codex exec failed/empty output"
        return candidates[0], meta

    try:
        obj = extract_json_object(last_msg)
        primary = str(obj.get("primary_ref") or "").strip().replace("\\", "/")
        reason = str(obj.get("reason") or "").strip()
        if primary not in candidates:
            raise ValueError("primary_ref not in candidates")
        meta["status"] = "ok"
        meta["primary_ref"] = primary
        meta["reason"] = reason
        return primary, meta
    except Exception as exc:
        meta["status"] = "fail"
        meta["error"] = str(exc)
        return candidates[0], meta
