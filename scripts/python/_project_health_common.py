#!/usr/bin/env python3
"""Common helpers for project-health scans and dashboard artifacts."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_HEALTH_KINDS = (
    "detect-project-stage",
    "doctor-project",
    "check-directory-boundaries",
)

TASK_FILES = ("tasks.json", "tasks_back.json", "tasks_gameplay.json")
ALLOWED_BASE_08_FILES = {"08-crosscutting-and-feature-slices.base.md"}
GODOT_PATTERN = re.compile(r"\busing\s+Godot\b|\bGodot\.", re.MULTILINE)
PRD_PATTERN = re.compile(r"\bPRD-[A-Za-z0-9_-]+\b")


def now_local() -> datetime:
    return datetime.now().astimezone()


def today_str(now: datetime | None = None) -> str:
    stamp = now or now_local()
    return stamp.strftime("%Y-%m-%d")


def timestamp_str(now: datetime | None = None) -> str:
    stamp = now or now_local()
    return stamp.strftime("%H%M%S%f")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_root(root: Path | str | None = None) -> Path:
    if root is None:
        return repo_root()
    return Path(root).resolve()


def to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def repo_rel(path: Path, *, root: Path) -> str:
    try:
        return to_posix(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return to_posix(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def history_dir(root: Path, *, now: datetime | None = None) -> Path:
    return root / "logs" / "ci" / today_str(now) / "project-health"


def latest_dir(root: Path) -> Path:
    return root / "logs" / "ci" / "project-health"


def task_triplet_paths(root: Path, parent: Path) -> dict[str, Path]:
    return {name: root / parent / name for name in TASK_FILES}


def has_task_triplet(paths: dict[str, Path]) -> bool:
    return all(path.exists() for path in paths.values())


def load_tasks_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def extract_tasks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    if isinstance(payload.get("tasks"), list):
        candidates = payload["tasks"]
    master = payload.get("master")
    if not candidates and isinstance(master, dict) and isinstance(master.get("tasks"), list):
        candidates = master["tasks"]
    return [item for item in candidates if isinstance(item, dict)]


def task_status_counts(root: Path) -> dict[str, int]:
    payload = load_tasks_payload(root / ".taskmaster" / "tasks" / "tasks.json")
    counts = {"in_progress": 0, "done": 0, "other": 0}
    for item in extract_tasks(payload):
        raw = str(item.get("status", "")).strip().lower().replace("-", "_")
        if raw in {"in_progress", "active", "working"}:
            counts["in_progress"] += 1
        elif raw in {"done", "completed", "closed"}:
            counts["done"] += 1
        else:
            counts["other"] += 1
    return counts


def overlay_indexes(root: Path) -> list[Path]:
    return sorted((root / "docs" / "architecture" / "overlays").glob("*/08/_index.md"))


def contract_files(root: Path) -> list[Path]:
    base = root / "Game.Core" / "Contracts"
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.cs") if path.is_file())


def unit_test_files(root: Path) -> list[Path]:
    candidates = []
    for rel in ("Game.Core.Tests", "Tests"):
        base = root / rel
        if not base.exists():
            continue
        candidates.extend(path for path in base.rglob("*.cs") if path.is_file() and not path.name.endswith(".uid"))
    return sorted(set(candidates))


def record_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['kind']}",
        "",
        f"- status: {payload.get('status', 'unknown')}",
        f"- summary: {payload.get('summary', '')}",
        f"- generated_at: {payload.get('generated_at', '')}",
    ]
    if "stage" in payload:
        lines.append(f"- stage: {payload['stage']}")
    if payload.get("history_json"):
        lines.append(f"- history_json: {payload['history_json']}")
    return "\n".join(lines).rstrip() + "\n"


def load_latest_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for kind in PROJECT_HEALTH_KINDS:
        path = latest_dir(root) / f"{kind}.latest.json"
        if path.exists():
            payload = read_json(path)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _normalize_report_value(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def _compact_extract_family_actions(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "family": _normalize_report_value(item.get("family"), limit=80),
                "count": int(item.get("count") or 0),
                "recommended_action": _normalize_report_value(item.get("recommended_action"), limit=120),
                "downstream_policy_hint": _normalize_report_value(item.get("downstream_policy_hint"), limit=40),
                "reason": _normalize_report_value(item.get("reason"), limit=200),
                "task_ids": [int(task_id) for task_id in list(item.get("task_ids") or [])[:12] if str(task_id).strip().isdigit()],
            }
        )
        if len(out) >= limit:
            break
    return out


def _compact_range_items(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "family": _normalize_report_value(item.get("family"), limit=80),
                "task_id_start": int(item.get("task_id_start") or 0),
                "task_id_end": int(item.get("task_id_end") or 0),
                "count": int(item.get("count") or 0),
                "reason": _normalize_report_value(item.get("reason"), limit=160),
            }
        )
        if len(out) >= limit:
            break
    return out


def _extract_report_highlights(payload: dict[str, Any]) -> dict[str, Any]:
    highlights: dict[str, Any] = {}
    family_actions = _compact_extract_family_actions(payload.get("extract_family_recommended_actions"))
    if family_actions:
        highlights["extract_family_recommended_actions"] = family_actions
    hotspots = _compact_range_items(payload.get("family_hotspots"))
    if hotspots:
        highlights["family_hotspots"] = hotspots
    quarantine = _compact_range_items(payload.get("quarantine_ranges"))
    if quarantine:
        highlights["quarantine_ranges"] = quarantine
    if not highlights:
        return {}
    if "covered_count" in payload:
        highlights["covered_count"] = int(payload.get("covered_count") or 0)
    if "failed_count" in payload:
        highlights["failed_count"] = int(payload.get("failed_count") or 0)
    return highlights


def build_report_catalog(root: Path) -> dict[str, Any]:
    """汇总 logs/ci 下可读取的 JSON 报告索引，供 latest.html 展示。"""
    logs_root = root / "logs" / "ci"
    if not logs_root.exists():
        return {"total_json": 0, "invalid_json": 0, "entries": []}

    entries: list[dict[str, Any]] = []
    invalid = 0
    for path in sorted(logs_root.rglob("*.json")):
        rel = repo_rel(path, root=root)
        try:
            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
        except OSError:
            stat = None
            modified_at = ""

        kind = path.stem
        status = ""
        generated_at = ""
        summary = ""
        parse_error = ""
        try:
            payload = read_json(path)
            if isinstance(payload, dict):
                kind = _normalize_report_value(payload.get("kind") or payload.get("cmd") or kind, limit=120) or kind
                status = _normalize_report_value(payload.get("status") or payload.get("result"), limit=40)
                generated_at = _normalize_report_value(
                    payload.get("generated_at") or payload.get("timestamp") or payload.get("ts"),
                    limit=60,
                )
                summary = _normalize_report_value(payload.get("summary") or payload.get("message"), limit=200)
                highlights = _extract_report_highlights(payload)
            else:
                parse_error = "json-not-object"
                highlights = {}
        except Exception:
            invalid += 1
            parse_error = "invalid-json"
            highlights = {}

        entries.append(
            {
                "path": rel,
                "kind": kind,
                "status": status,
                "generated_at": generated_at,
                "summary": summary,
                "size_bytes": int(stat.st_size) if stat else 0,
                "modified_at": modified_at,
                "parse_error": parse_error,
                "highlights": highlights,
            }
        )

    entries.sort(key=lambda item: (item.get("modified_at", ""), item.get("path", "")), reverse=True)
    return {
        "total_json": len(entries),
        "invalid_json": invalid,
        "entries": entries,
    }


def dashboard_html(
    records: list[dict[str, Any]],
    *,
    generated_at: str,
    report_catalog: dict[str, Any],
    report_catalog_path: str,
) -> str:
    overall = "ok"
    if any(item.get("status") == "fail" for item in records):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in records):
        overall = "warn"

    cards = []
    for item in records:
        kind = html.escape(str(item.get("kind", "unknown")))
        status = html.escape(str(item.get("status", "unknown")))
        summary = html.escape(str(item.get("summary", "")))
        extra = []
        if item.get("stage"):
            extra.append(f"<div class=\"meta\">阶段: {html.escape(str(item['stage']))}</div>")
        if item.get("history_json"):
            extra.append(f"<div class=\"meta\">历史: {html.escape(str(item['history_json']))}</div>")
        cards.append(
            "\n".join(
                [
                    f"<section class=\"card {status}\">",
                    f"<h2>{kind}</h2>",
                    f"<div class=\"badge\">{status}</div>",
                    f"<p>{summary}</p>",
                    *extra,
                    f"<div class=\"meta\">latest json: {kind}.latest.json</div>",
                    "</section>",
                ]
            )
        )

    highlight_sections = []
    highlighted_entries = [
        item for item in report_catalog.get("entries", []) if isinstance(item, dict) and isinstance(item.get("highlights"), dict) and item.get("highlights")
    ][:4]
    for item in highlighted_entries:
        highlights = dict(item.get("highlights") or {})
        lines = [
            f"<section class=\"highlight-card\">",
            f"<h3>{html.escape(str(item.get('kind', 'unknown')))}</h3>",
            f"<div class=\"meta\">path: {html.escape(str(item.get('path', '')))}</div>",
            f"<div class=\"meta\">status: {html.escape(str(item.get('status', 'unknown') or 'unknown'))}</div>",
        ]
        if "covered_count" in highlights or "failed_count" in highlights:
            lines.append(
                f"<div class=\"meta\">covered={int(highlights.get('covered_count') or 0)} failed={int(highlights.get('failed_count') or 0)}</div>"
            )
        family_actions = highlights.get("extract_family_recommended_actions") or []
        if family_actions:
            lines.append("<div class=\"subhead\">Extract failure families</div>")
            for family_item in family_actions:
                lines.append("<div class=\"highlight-item\">")
                lines.append(
                    f"<div><strong>{html.escape(str(family_item.get('family') or 'unknown'))}</strong> "
                    f"(<span>{int(family_item.get('count') or 0)}</span>)</div>"
                )
                lines.append(
                    f"<div class=\"meta\">hint: {html.escape(str(family_item.get('downstream_policy_hint') or 'manual'))} | "
                    f"action: {html.escape(str(family_item.get('recommended_action') or 'inspect'))}</div>"
                )
                if family_item.get("task_ids"):
                    lines.append(f"<div class=\"meta\">tasks: {html.escape(','.join(str(task_id) for task_id in family_item['task_ids']))}</div>")
                if family_item.get("reason"):
                    lines.append(f"<div class=\"meta\">reason: {html.escape(str(family_item['reason']))}</div>")
                lines.append("</div>")
        hotspots = highlights.get("family_hotspots") or []
        if hotspots:
            lines.append("<div class=\"subhead\">Family hotspots</div>")
            for hotspot in hotspots:
                lines.append(
                    f"<div class=\"meta\">{html.escape(str(hotspot.get('family') or 'unknown'))}: "
                    f"T{int(hotspot.get('task_id_start') or 0)}-T{int(hotspot.get('task_id_end') or 0)} "
                    f"count={int(hotspot.get('count') or 0)}</div>"
                )
        quarantine = highlights.get("quarantine_ranges") or []
        if quarantine:
            lines.append("<div class=\"subhead\">Quarantine ranges</div>")
            for item_range in quarantine:
                lines.append(
                    f"<div class=\"meta\">{html.escape(str(item_range.get('family') or 'unknown'))}: "
                    f"T{int(item_range.get('task_id_start') or 0)}-T{int(item_range.get('task_id_end') or 0)} "
                    f"{html.escape(str(item_range.get('reason') or ''))}</div>"
                )
        lines.append("</section>")
        highlight_sections.append("\n".join(lines))

    report_rows = []
    for item in report_catalog.get("entries", []):
        parse_error = str(item.get("parse_error") or "")
        status_text = str(item.get("status") or "")
        status_cls = "invalid" if parse_error else ("ok" if status_text in {"ok", "pass", "passed"} else ("warn" if status_text == "warn" else ("fail" if status_text == "fail" else "unknown")))
        report_rows.append(
            "\n".join(
                [
                    "<tr>",
                    f"<td>{html.escape(str(item.get('modified_at', '')))}</td>",
                    f"<td>{html.escape(str(item.get('kind', '')))}</td>",
                    f"<td><span class=\"chip {status_cls}\">{html.escape(status_text or parse_error or 'n/a')}</span></td>",
                    f"<td>{html.escape(str(item.get('generated_at', '')))}</td>",
                    f"<td>{html.escape(str(item.get('path', '')))}</td>",
                    f"<td>{html.escape(str(item.get('summary', '')))}</td>",
                    "</tr>",
                ]
            )
        )

    report_total = int(report_catalog.get("total_json", 0))
    report_invalid = int(report_catalog.get("invalid_json", 0))
    report_catalog_path_escaped = html.escape(report_catalog_path)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Project Health Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #f4f6f8; color: #1f2933; margin: 0; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .hero {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
    .status {{ padding: 6px 12px; border-radius: 999px; font-weight: 700; text-transform: uppercase; }}
    .status.ok {{ background: #d1fae5; color: #065f46; }}
    .status.warn {{ background: #fef3c7; color: #92400e; }}
    .status.fail {{ background: #fee2e2; color: #991b1b; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ background: #ffffff; border: 1px solid #d2d6dc; border-left-width: 6px; border-radius: 12px; padding: 18px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08); }}
    .card.ok {{ border-left-color: #10b981; }}
    .card.warn {{ border-left-color: #f59e0b; }}
    .card.fail {{ border-left-color: #ef4444; }}
    .card h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .badge {{ display: inline-block; margin-bottom: 10px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .meta {{ color: #52606d; font-size: 12px; margin-top: 8px; word-break: break-all; }}
    .hint {{ margin-top: 20px; color: #52606d; font-size: 13px; }}
    .actions {{ display: flex; gap: 8px; margin-top: 8px; }}
    .btn {{ border: 1px solid #cbd2d9; border-radius: 8px; background: #fff; padding: 6px 10px; font-size: 13px; cursor: pointer; }}
    .btn:hover {{ background: #f8fafc; }}
    .table-wrap {{ margin-top: 18px; overflow: auto; background: #fff; border: 1px solid #d2d6dc; border-radius: 12px; }}
    .highlight-wrap {{ margin-top: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .highlight-card {{ background: #fff; border: 1px solid #d2d6dc; border-radius: 12px; padding: 16px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06); }}
    .highlight-card h3 {{ margin: 0 0 10px; font-size: 16px; }}
    .highlight-item {{ border-top: 1px solid #e5e7eb; padding-top: 10px; margin-top: 10px; }}
    .subhead {{ margin-top: 12px; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #52606d; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; vertical-align: top; }}
    th {{ background: #f8fafc; position: sticky; top: 0; z-index: 1; }}
    .chip {{ display: inline-block; padding: 2px 6px; border-radius: 999px; font-weight: 700; }}
    .chip.ok {{ background: #d1fae5; color: #065f46; }}
    .chip.warn {{ background: #fef3c7; color: #92400e; }}
    .chip.fail {{ background: #fee2e2; color: #991b1b; }}
    .chip.invalid {{ background: #e5e7eb; color: #1f2933; }}
    .chip.unknown {{ background: #e0e7ff; color: #3730a3; }}
  </style>
</head>
<body>
  <!-- 仪表盘说明：本页面不自动刷新，避免阅读过程中跳页。 -->
  <!-- 报告索引说明：下方表格来自 logs/ci/** 的 JSON 报告聚合。 -->
  <main>
    <div class="hero">
      <div>
        <h1>项目健康总览</h1>
        <div>该页面聚合项目健康检查结果 + logs/ci 下可整合的 JSON 报告索引。</div>
        <div class="actions">
          <button class="btn" onclick="window.location.reload()">手动刷新</button>
        </div>
      </div>
      <div class="status {overall}">{overall}</div>
    </div>
    <div class="meta">generated_at: {generated_at}</div>
    <div class="grid">
      {''.join(cards)}
    </div>
    <details open>
      <summary>批量任务诊断摘录</summary>
      <div class="hint">这里优先展示报告 JSON 里可直接消费的高价值字段，例如 extract family 建议动作、family hotspot、quarantine 范围。</div>
      <div class="highlight-wrap">
        {''.join(highlight_sections) if highlight_sections else '<div class="meta">当前没有可直接展示的批量诊断摘要。</div>'}
      </div>
    </details>
    <div class="hint">JSON 报告总数: {report_total}；解析失败: {report_invalid}；索引文件: {report_catalog_path_escaped}</div>
    <details>
      <summary>展开查看全部 JSON 报告索引</summary>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>modified_at</th>
              <th>kind</th>
              <th>status</th>
              <th>generated_at</th>
              <th>path</th>
              <th>summary</th>
            </tr>
          </thead>
          <tbody>
            {''.join(report_rows)}
          </tbody>
        </table>
      </div>
    </details>
  </main>
</body>
</html>
"""


def refresh_dashboard(root: Path | str | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    stamp = now or now_local()
    records = load_latest_records(resolved_root)
    report_catalog = build_report_catalog(resolved_root)
    overall = "ok"
    if any(item.get("status") == "fail" for item in records):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in records):
        overall = "warn"
    payload = {
        "kind": "project-health-dashboard",
        "status": overall,
        "generated_at": stamp.isoformat(timespec="seconds"),
        "records": [
            {
                "kind": item.get("kind", ""),
                "status": item.get("status", ""),
                "summary": item.get("summary", ""),
                "stage": item.get("stage", ""),
                "latest_json": f"{item.get('kind', '')}.latest.json",
                "history_json": item.get("history_json", ""),
            }
            for item in records
        ],
        "report_catalog_summary": {
            "total_json": int(report_catalog.get("total_json", 0)),
            "invalid_json": int(report_catalog.get("invalid_json", 0)),
            "catalog_json": "logs/ci/project-health/report-catalog.latest.json",
        },
    }
    latest_root = latest_dir(resolved_root)
    report_catalog_path = latest_root / "report-catalog.latest.json"
    write_json(report_catalog_path, report_catalog)
    write_json(latest_root / "latest.json", payload)
    write_text(
        latest_root / "latest.html",
        dashboard_html(
            records,
            generated_at=payload["generated_at"],
            report_catalog=report_catalog,
            report_catalog_path=repo_rel(report_catalog_path, root=resolved_root),
        ),
    )
    return payload


def write_project_health_record(
    *,
    root: Path | str | None,
    kind: str,
    payload: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, str]:
    resolved_root = resolve_root(root)
    stamp = now or now_local()
    history_root = history_dir(resolved_root, now=stamp)
    latest_root = latest_dir(resolved_root)
    history_json = history_root / f"{kind}-{timestamp_str(stamp)}.json"
    latest_json = latest_root / f"{kind}.latest.json"
    latest_md = latest_root / f"{kind}.latest.md"

    record = dict(payload)
    record["kind"] = kind
    record.setdefault("generated_at", stamp.isoformat(timespec="seconds"))
    record["history_json"] = repo_rel(history_json, root=resolved_root)
    record["latest_json"] = repo_rel(latest_json, root=resolved_root)

    write_json(history_json, record)
    write_json(latest_json, record)
    write_text(latest_md, record_markdown(record))
    refresh_dashboard(resolved_root, now=stamp)
    return {
        "history_json": repo_rel(history_json, root=resolved_root),
        "latest_json": repo_rel(latest_json, root=resolved_root),
        "latest_md": repo_rel(latest_md, root=resolved_root),
        "dashboard_html": repo_rel(latest_root / "latest.html", root=resolved_root),
    }
