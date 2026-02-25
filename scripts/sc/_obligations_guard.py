#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Any
from _obligations_prompt_acceptance import build_acceptance_prompt_blocks
_ANTI_TAMPER_TERMS: tuple[str, ...] = (
    "anti tamper",
    "anti-tamper",
    "tamper",
    "hmac",
    "signature",
    "checksum",
    "hash chain",
    "chain-hash",
    "integrity",
    "trusted publisher",
    "anti cheat",
    "anti-cheat",
    "防篡改",
    "篡改",
    "签名",
    "完整性",
    "校验",
    "哈希链",
    "链式哈希",
)

_HOST_SAFETY_TERMS: tuple[str, ...] = (
    "res://",
    "user://",
    "path traversal",
    "absolute path",
    "sql injection",
    "allowlist",
    "https",
    "os.execute",
    "dynamic load",
    "remote debug",
    "路径越权",
    "绝对路径",
    "注入",
    "白名单",
)

_MIN_STRIPPED_EXCERPT_LEN = 12
_MIN_STRIPPED_EN_WORDS = 3
_MIN_STRIPPED_ZH_CHARS = 6


def normalize_model_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return "ok" if status == "ok" else "fail"


def parse_subtask_source(source: Any) -> str | None:
    text = str(source or "").strip()
    match = re.match(r"subtask\s*:\s*(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return None
    sid = str(match.group(1) or "").strip()
    return sid or None


def safe_prompt_truncate(prompt: str, *, max_chars: int) -> str:
    text = str(prompt or "")
    limit = max(1_000, int(max_chars))
    if len(text) <= limit:
        return text
    tail_keep = min(6_000, max(1_200, limit // 2))
    head_keep = max(200, limit - tail_keep - 64)
    if head_keep + tail_keep >= limit:
        return text[:limit]
    return (
        text[:head_keep]
        + "\n\n...[PROMPT_TRUNCATED_FOR_BUDGET]...\n\n"
        + text[-tail_keep:]
    )


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _strip_prompt_prefix(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return s
    patterns = (
        r"^Task:\s*T\d+\s*[:：\-]?\s*",
        r"^Master\s+title:\s*",
        r"^任务[:：]\s*T?\d+\s*[:：\-]?\s*",
        r"^主标题[:：]\s*",
    )
    for pat in patterns:
        s2 = re.sub(pat, "", s, flags=re.IGNORECASE).strip()
        if s2 != s:
            s = s2
    return s


def _passes_stripped_excerpt_quality(norm_text: str) -> bool:
    text = str(norm_text or "").strip()
    if not text:
        return False
    en_words = len(re.findall(r"[A-Za-z]{2,}", text))
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return en_words >= _MIN_STRIPPED_EN_WORDS or zh_chars >= _MIN_STRIPPED_ZH_CHARS


def _contains_excerpt(excerpt: str, raw_corpus: str, norm_corpus: str) -> tuple[bool, bool]:
    """Return (matched, matched_after_prefix_strip)."""
    if not excerpt:
        return False, False

    def _match(candidate: str) -> bool:
        if not candidate:
            return False
        if candidate in raw_corpus:
            return True
        norm_candidate = _normalize_ws(candidate)
        return bool(norm_candidate and norm_candidate in norm_corpus)

    if _match(excerpt):
        return True, False

    stripped = _strip_prompt_prefix(excerpt)
    norm_stripped = _normalize_ws(stripped)
    if (
        stripped
        and stripped != excerpt
        and len(norm_stripped) >= _MIN_STRIPPED_EXCERPT_LEN
        and _passes_stripped_excerpt_quality(norm_stripped)
        and _match(stripped)
    ):
        return True, True

    return False, False


def _is_anti_tamper_only(text: str) -> bool:
    lower = str(text or "").lower()
    if not lower:
        return False
    has_anti_tamper = any(term in lower for term in _ANTI_TAMPER_TERMS)
    if not has_anti_tamper:
        return False
    has_host_safety = any(term in lower for term in _HOST_SAFETY_TERMS)
    return not has_host_safety


def _dedupe_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _count_uncovered(obj: dict[str, Any]) -> int:
    raw = obj.get("uncovered_obligation_ids") or []
    if not isinstance(raw, list):
        return 0
    return len([x for x in raw if str(x or "").strip()])


def pick_consensus_verdict(
    run_verdicts: list[dict[str, Any]],
    *,
    target_status: str,
) -> dict[str, Any] | None:
    if not run_verdicts:
        return None
    target = "ok" if str(target_status).strip().lower() == "ok" else "fail"
    candidates = [x for x in run_verdicts if normalize_model_status(x.get("status")) == target]
    if not candidates:
        return run_verdicts[0]

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        obj = item.get("obj") if isinstance(item.get("obj"), dict) else {}
        uncovered_count = _count_uncovered(obj)
        run = int(item.get("run") or 999_999)
        if target == "fail":
            return (-uncovered_count, run)
        return (uncovered_count, run)

    return sorted(candidates, key=sort_key)[0]


def apply_deterministic_guards(
    *,
    obj: dict[str, Any],
    subtasks: list[dict[str, str]],
    min_obligations: int,
    source_text_blocks: list[str],
    security_profile: str,
) -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    status = normalize_model_status(obj.get("status"))
    obligations = obj.get("obligations") or []
    if not isinstance(obligations, list):
        obligations = []
    obj["obligations"] = obligations

    det_issues: list[str] = []
    advisory_uncovered: list[str] = []
    hard_uncovered: list[str] = []
    prefix_stripped_match_count = 0

    if int(min_obligations) > 0 and len(obligations) < int(min_obligations):
        det_issues.append(f"DET_MIN_OBLIGATIONS<{int(min_obligations)}")

    subtask_ids = [str(s.get("id") or "").strip() for s in subtasks if str(s.get("id") or "").strip()]
    subtask_id_set = set(subtask_ids)
    covered_sources: set[str] = set()

    raw_corpus = "\n".join([str(x or "") for x in source_text_blocks if str(x or "").strip()])
    norm_corpus = _normalize_ws(raw_corpus)

    expected_hard_uncovered: list[str] = []
    for index, obligation in enumerate(obligations, start=1):
        if not isinstance(obligation, dict):
            det_issues.append(f"DET_OBLIGATION_NOT_OBJECT:{index}")
            continue
        oid = str(obligation.get("id") or f"O{index}").strip()
        obligation["id"] = oid
        source = str(obligation.get("source") or "").strip()
        text = str(obligation.get("text") or "").strip()
        excerpt = str(obligation.get("source_excerpt") or "").strip()
        covered = bool(obligation.get("covered"))

        if not text:
            det_issues.append(f"DET_OBLIGATION_TEXT_EMPTY:{oid}")

        if not excerpt:
            det_issues.append(f"DET_SOURCE_EXCERPT_EMPTY:{oid}")
        elif raw_corpus:
            found, matched_after_strip = _contains_excerpt(excerpt, raw_corpus, norm_corpus)
            if not found:
                det_issues.append(f"DET_SOURCE_EXCERPT_NOT_FOUND:{oid}")
            elif matched_after_strip:
                prefix_stripped_match_count += 1

        if source.lower() != "master":
            sid = parse_subtask_source(source)
            if not sid:
                det_issues.append(f"DET_SOURCE_INVALID:{oid}")
            else:
                if sid not in subtask_id_set:
                    det_issues.append(f"DET_SUBTASK_SOURCE_UNKNOWN:{sid}")
                covered_sources.add(sid)

        if not covered:
            anti_tamper_probe = f"{text} {excerpt} {source}"
            if security_profile == "host-safe" and _is_anti_tamper_only(anti_tamper_probe):
                advisory_uncovered.append(oid)
            else:
                hard_uncovered.append(oid)
                expected_hard_uncovered.append(oid)

    for sid in subtask_ids:
        if sid not in covered_sources:
            det_issues.append(f"DET_SUBTASK_SOURCE:{sid}")

    declared_uncovered = obj.get("uncovered_obligation_ids") or []
    declared_uncovered_ids = _dedupe_keep_order([str(x or "") for x in declared_uncovered]) if isinstance(declared_uncovered, list) else []
    for oid in expected_hard_uncovered:
        if oid not in declared_uncovered_ids:
            det_issues.append(f"DET_UNCOVERED_MISSING:{oid}")

    hard_uncovered = _dedupe_keep_order(hard_uncovered)
    advisory_uncovered = _dedupe_keep_order(advisory_uncovered)

    if status == "ok" and hard_uncovered:
        det_issues.append("DET_STATUS_OK_WITH_HARD_UNCOVERED")

    if status == "fail" and not hard_uncovered and advisory_uncovered and not det_issues:
        status = "ok"

    if hard_uncovered or det_issues:
        status = "fail"

    notes = obj.get("notes") or []
    if not isinstance(notes, list):
        notes = []
    notes.extend([f"deterministic_hard_gate: {x}" for x in det_issues])
    if advisory_uncovered:
        notes.append(
            "host_safe_advisory: anti-tamper-only uncovered obligations are advisory under host-safe profile."
        )

    obj["notes"] = notes
    obj["status"] = status
    obj["uncovered_obligation_ids"] = hard_uncovered
    obj["advisory_uncovered_obligation_ids"] = advisory_uncovered
    obj["source_excerpt_prefix_stripped_matches"] = prefix_stripped_match_count

    return obj, det_issues, hard_uncovered, advisory_uncovered


def render_obligations_report(obj: dict[str, Any]) -> str:
    task_id = str(obj.get("task_id") or "")
    status = str(obj.get("status") or "")
    uncovered = obj.get("uncovered_obligation_ids") or []
    advisory = obj.get("advisory_uncovered_obligation_ids") or []
    obligations = obj.get("obligations") or []
    lines: list[str] = []
    lines.append("# sc-llm-extract-task-obligations report")
    lines.append("")
    lines.append(f"- task_id: {task_id}")
    lines.append(f"- status: {status}")
    lines.append(f"- uncovered(hard): {len(uncovered) if isinstance(uncovered, list) else 'unknown'}")
    lines.append(f"- uncovered(advisory): {len(advisory) if isinstance(advisory, list) else 'unknown'}")
    lines.append(f"- excerpt_prefix_stripped_matches: {int(obj.get('source_excerpt_prefix_stripped_matches') or 0)}")
    lines.append("")
    if isinstance(obligations, list) and obligations:
        lines.append("## Obligations")
        lines.append("")
        for raw in obligations:
            if not isinstance(raw, dict):
                continue
            oid = str(raw.get("id") or "").strip()
            covered = bool(raw.get("covered"))
            text = str(raw.get("text") or "").strip()
            excerpt = str(raw.get("source_excerpt") or "").strip()
            source = str(raw.get("source") or "").strip()
            kind = str(raw.get("kind") or "").strip()
            lines.append(f"- {oid} covered={covered} kind={kind} source={source}: {text}")
            if excerpt:
                lines.append(f"  - excerpt: {excerpt}")
    notes = obj.get("notes") or []
    if isinstance(notes, list) and notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            text = str(note or "").strip()
            if text:
                lines.append(f"- {text}")
    return "\n".join(lines).strip() + "\n"


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def build_obligation_prompt(
    *,
    task_id: str,
    title: str,
    master_details: str,
    master_test_strategy: str,
    subtasks: list[dict[str, str]],
    acceptance_by_view: dict[str, list[Any]],
    security_profile: str,
    security_profile_context: str,
) -> str:
    subtask_lines: list[str] = []
    for item in subtasks:
        sid = item.get("id", "").strip()
        sub_title = item.get("title", "").strip()
        sub_details = item.get("details", "").strip()
        sub_test_strategy = item.get("testStrategy", "").strip()
        if sid and sub_title:
            line = f"- {sid}: {sub_title}"
            if sub_details:
                line += f" :: {sub_details}"
            subtask_lines.append(line)
            if sub_test_strategy:
                subtask_lines.append(f"  testStrategy: {sub_test_strategy}")

    acceptance_blocks = build_acceptance_prompt_blocks(acceptance_by_view)

    schema = """
Return JSON only (no Markdown).
Schema:
{
  "task_id": "<id>",
  "status": "ok" | "fail",
  "obligations": [
    {
      "id": "O1",
      "source": "master" | "subtask:<id>",
      "kind": "core" | "godot" | "meta",
      "text": "<one falsifiable obligation>",
      "source_excerpt": "<short verbatim excerpt from the provided task text>",
      "covered": true | false,
      "matches": [
        {"view": "back|gameplay", "acceptance_index": <1-based>, "acceptance_excerpt": "<short>"}
      ],
      "reason": "<one short sentence>",
      "suggested_acceptance": ["<line1>", "<line2>"]
    }
  ],
  "uncovered_obligation_ids": ["O2", "..."],
  "notes": ["<short>", ...]
}

Rules:
- Obligations MUST be falsifiable / auditable: avoid vague statements like "works correctly".
- Avoid no-op loopholes: include at least one "must refuse / must not advance / state unchanged" obligation when applicable.
- Use ONLY the provided task text (master.title/details/testStrategy + subtasks title/details/testStrategy) to derive obligations.
- Each obligation MUST include source_excerpt copied verbatim from the provided task text; if you cannot cite an excerpt, do NOT include that obligation.
- source_excerpt MUST NOT quote prompt headers such as "Task: T<id>" or "Master title:".
- acceptance section is deduplicated; when filling matches.acceptance_index, use the original source index listed in "sources" (e.g., back:3).
- Be conservative: mark covered ONLY when an acceptance item clearly implies it.
- If ANY obligation is not covered => status must be "fail".
- suggested_acceptance must be minimal and aligned to tasks_back/tasks_gameplay style (Chinese OK). Do NOT include any "Refs:" here.
- Ignore "Local demo paths" / absolute paths; they are not obligations.

Security profile rules:
- profile=%s
- host-safe: anti-tamper-only obligations are advisory unless explicitly required by the provided task text.
- strict: enforce all uncovered obligations as hard failures.
""" % security_profile

    details_block = _truncate(master_details or "", max_chars=8_000)
    test_strategy_block = _truncate(master_test_strategy or "", max_chars=4_000)

    return "\n".join(
        [
            "You are a strict reviewer for a Godot + C# repo.",
            "Acceptance criteria are used as SSoT for deterministic gates; they must cover all must-have obligations.",
            "",
            f"Task: T{task_id} {title}",
            "",
            "Master title:",
            _truncate(title or "", max_chars=600) or "(empty)",
            "",
            "Security profile context:",
            security_profile_context.strip() or f"- profile: {security_profile}",
            "",
            "Master details:",
            details_block or "(empty)",
            "",
            "Master testStrategy:",
            test_strategy_block or "(empty)",
            "",
            "Subtasks (from tasks.json):",
            *(subtask_lines or ["- (none)"]),
            "",
            "Acceptance criteria (from tasks_back/tasks_gameplay):",
            *acceptance_blocks,
            "",
            schema.strip(),
        ]
    )
