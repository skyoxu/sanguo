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


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_flat_kv(items: dict[str, Any]) -> str:
    if not items:
        return "<div class=\"meta\">no details</div>"
    rows = []
    for key in sorted(items.keys()):
        rows.append(
            "<tr>"
            f"<th>{_h(key)}</th>"
            f"<td>{_h(items[key])}</td>"
            "</tr>"
        )
    return "<table class=\"kv-table\"><tbody>" + "".join(rows) + "</tbody></table>"


def _render_checks(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "<div class=\"meta\">no checks</div>"
    rows = []
    for item in checks:
        rows.append(
            "<tr>"
            f"<td>{_h(item.get('id', ''))}</td>"
            f"<td>{_h(item.get('status', ''))}</td>"
            f"<td>{_h(item.get('summary', ''))}</td>"
            f"<td>{_h(item.get('recommendation', ''))}</td>"
            "</tr>"
        )
    return (
        "<table class=\"list-table\"><thead><tr>"
        "<th>id</th><th>status</th><th>summary</th><th>recommendation</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_findings(items: list[dict[str, Any]], *, label: str) -> str:
    if not items:
        return f"<div class=\"meta\">{_h(label)}: none</div>"
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{_h(item.get('rule_id', item.get('type', '')))}</td>"
            f"<td>{_h(item.get('path', ''))}</td>"
            f"<td>{_h(item.get('message', item.get('summary', '')))}</td>"
            "</tr>"
        )
    return (
        f"<div class=\"meta\">{_h(label)}: {len(items)}</div>"
        "<table class=\"list-table\"><thead><tr>"
        "<th>rule/type</th><th>path</th><th>message</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_record_details(item: dict[str, Any]) -> str:
    kind = str(item.get("kind", ""))
    sections: list[str] = []

    counts = item.get("counts")
    if isinstance(counts, dict):
        sections.append("<h4>Counts</h4>" + _render_flat_kv(counts))

    signals = item.get("signals")
    if isinstance(signals, dict):
        sections.append("<h4>Signals</h4>" + _render_flat_kv(signals))

    checks = item.get("checks")
    if isinstance(checks, list):
        sections.append("<h4>Checks</h4>" + _render_checks([x for x in checks if isinstance(x, dict)]))

    violations = item.get("violations")
    if isinstance(violations, list):
        sections.append("<h4>Violations</h4>" + _render_findings([x for x in violations if isinstance(x, dict)], label="violations"))

    warnings = item.get("warnings")
    if isinstance(warnings, list):
        sections.append("<h4>Warnings</h4>" + _render_findings([x for x in warnings if isinstance(x, dict)], label="warnings"))

    if not sections:
        if kind == "detect-project-stage":
            sections.append("<div class=\"meta\">No extra fields recorded for this stage snapshot.</div>")
        else:
            sections.append("<div class=\"meta\">No expandable details in this record.</div>")
    return "".join(sections)


def dashboard_html(records: list[dict[str, Any]], *, generated_at: str) -> str:
    overall = "ok"
    if any(item.get("status") == "fail" for item in records):
        overall = "fail"
    elif any(item.get("status") == "warn" for item in records):
        overall = "warn"

    total = len(records)
    fail_count = sum(1 for item in records if item.get("status") == "fail")
    warn_count = sum(1 for item in records if item.get("status") == "warn")
    ok_count = sum(1 for item in records if item.get("status") == "ok")

    cards = []
    for item in records:
        kind = str(item.get("kind", "unknown"))
        status = str(item.get("status", "unknown"))
        summary = str(item.get("summary", ""))
        latest_json_name = f"{kind}.latest.json"
        history_json = str(item.get("history_json", ""))
        details_html = _render_record_details(item)
        extra = []
        if item.get("stage"):
            extra.append(f"<div class=\"meta\">stage: {_h(item['stage'])}</div>")
        extra.append(f"<div class=\"meta\">latest json: <a href=\"{_h(latest_json_name)}\" target=\"_blank\" rel=\"noopener\">{_h(latest_json_name)}</a></div>")
        if history_json:
            extra.append(
                "<div class=\"meta\">history json: "
                f"<a href=\"{_h(history_json)}\" target=\"_blank\" rel=\"noopener\">{_h(history_json)}</a>"
                "</div>"
            )
        cards.append(
            "\n".join(
                [
                    f"<section class=\"card {status}\">",
                    f"<h2>{_h(kind)}</h2>",
                    f"<div class=\"badge\">{_h(status)}</div>",
                    f"<p>{_h(summary)}</p>",
                    *extra,
                    "<details class=\"details\">",
                    "<summary>Expand details</summary>",
                    f"<div class=\"details-body\">{details_html}</div>",
                    "</details>",
                    "</section>",
                ]
            )
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Project Health Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #f4f6f8; color: #1f2933; margin: 0; }}
    main {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
    .hero {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
    .status {{ padding: 6px 12px; border-radius: 999px; font-weight: 700; text-transform: uppercase; }}
    .status.ok {{ background: #d1fae5; color: #065f46; }}
    .status.warn {{ background: #fef3c7; color: #92400e; }}
    .status.fail {{ background: #fee2e2; color: #991b1b; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ background: #ffffff; border: 1px solid #d2d6dc; border-left-width: 6px; border-radius: 12px; padding: 18px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08); }}
    .card.ok {{ border-left-color: #10b981; }}
    .card.warn {{ border-left-color: #f59e0b; }}
    .card.fail {{ border-left-color: #ef4444; }}
    .card h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .badge {{ display: inline-block; margin-bottom: 10px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .meta {{ color: #52606d; font-size: 12px; margin-top: 8px; word-break: break-all; }}
    .summary-grid {{ margin-top: 12px; display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 8px; }}
    .pill {{ background: #fff; border: 1px solid #d2d6dc; border-radius: 10px; padding: 8px 10px; font-size: 13px; }}
    .details {{ margin-top: 12px; border-top: 1px dashed #cbd2d9; padding-top: 10px; }}
    .details summary {{ cursor: pointer; font-weight: 600; color: #334e68; }}
    .details-body {{ margin-top: 10px; }}
    .details-body h4 {{ margin: 10px 0 6px; font-size: 13px; color: #334e68; }}
    .kv-table, .list-table {{ width: 100%; border-collapse: collapse; font-size: 12px; background: #fbfcfd; }}
    .kv-table th, .kv-table td, .list-table th, .list-table td {{ border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; vertical-align: top; }}
    .kv-table th, .list-table th {{ width: 25%; background: #f0f4f8; color: #334e68; font-weight: 600; }}
    a {{ color: #0f4c81; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .hint {{ margin-top: 20px; color: #52606d; font-size: 13px; }}
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <div>
        <h1>Project Health Dashboard</h1>
        <div>Latest stage, doctor, and directory-boundary records for this repo.</div>
      </div>
      <div class="status {overall}">{overall}</div>
    </div>
    <div class="meta">generated_at: {_h(generated_at)}</div>
    <div class="summary-grid">
      <div class="pill">total: {_h(total)}</div>
      <div class="pill">ok: {_h(ok_count)}</div>
      <div class="pill">warn: {_h(warn_count)}</div>
      <div class="pill">fail: {_h(fail_count)}</div>
    </div>
    <div class="meta">raw index: <a href="latest.json" target="_blank" rel="noopener">latest.json</a></div>
    <div class="grid">
      {''.join(cards)}
    </div>
    <div class="hint">Refresh is automatic every 15 seconds. The page only changes when one of the project-health commands writes a new latest record.</div>
  </main>
</body>
</html>
"""


def refresh_dashboard(root: Path | str | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    stamp = now or now_local()
    records = load_latest_records(resolved_root)
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
    }
    latest_root = latest_dir(resolved_root)
    write_json(latest_root / "latest.json", payload)
    write_text(latest_root / "latest.html", dashboard_html(records, generated_at=payload["generated_at"]))
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
