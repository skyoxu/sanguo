#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_tasks_file(root: Path) -> Path:
    primary = root / ".taskmaster" / "tasks" / "tasks.json"
    if primary.exists():
        return primary
    fallback = root / "examples" / "taskmaster" / "tasks.json"
    return fallback


def parse_task_ids_csv(text: str) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for token in (text or "").split(","):
        value = token.strip()
        if not value:
            continue
        if value.lower().startswith("t"):
            value = value[1:]
        if not value.isdigit():
            raise ValueError(f"invalid task id token: {token!r}")
        task_id = int(value)
        if task_id <= 0 or task_id in seen:
            continue
        seen.add(task_id)
        ids.append(task_id)
    return ids


def load_task_ids_from_file(path: Path, limit: int) -> list[int]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    tasks: list[Any]
    if isinstance(data, dict) and isinstance(data.get("master"), dict) and isinstance(data["master"].get("tasks"), list):
        tasks = data["master"]["tasks"]
    elif isinstance(data, dict) and isinstance(data.get("tasks"), list):
        tasks = data["tasks"]
    elif isinstance(data, list):
        tasks = data
    else:
        tasks = []

    result: list[int] = []
    seen: set[int] = set()
    for item in tasks:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if isinstance(raw_id, int):
            task_id = raw_id
        elif isinstance(raw_id, str) and raw_id.strip().isdigit():
            task_id = int(raw_id.strip())
        else:
            continue
        if task_id <= 0 or task_id in seen:
            continue
        seen.add(task_id)
        result.append(task_id)
        if len(result) >= max(1, limit):
            break
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun llm_extract_task_obligations across task ids for jitter hard-gate evidence.")
    parser.add_argument("--task-ids", default="", help="CSV task ids (e.g. 1,2,3 or T1,T2). Empty means load from --tasks-file.")
    parser.add_argument("--tasks-file", default="", help="Task JSON file path. Empty means auto-resolve .taskmaster/tasks/tasks.json then examples/taskmaster/tasks.json.")
    parser.add_argument("--max-tasks", type=int, default=5, help="Maximum number of task ids auto-loaded from --tasks-file.")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rerun rounds per task.")
    parser.add_argument("--timeout-sec", type=int, default=420, help="Timeout passed to llm_extract_task_obligations.py.")
    parser.add_argument("--delivery-profile", default="", help="Optional delivery profile passed through.")
    parser.add_argument("--security-profile", default="", choices=["", "strict", "host-safe"], help="Optional security profile override passed through.")
    parser.add_argument("--out-dir", default="", help="Output dir. Default: logs/ci/<today>/")
    parser.add_argument("--out-json", default="", help="Output JSON file path.")
    parser.add_argument("--out-md", default="", help="Output markdown file path.")
    return parser.parse_args()


def build_cmd(args: argparse.Namespace, task_id: int, round_index: int) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/sc/llm_extract_task_obligations.py",
        "--task-id",
        str(task_id),
        "--timeout-sec",
        str(args.timeout_sec),
        "--round-id",
        f"hardgate-r{round_index}",
    ]
    if str(args.delivery_profile).strip():
        cmd.extend(["--delivery-profile", args.delivery_profile.strip()])
    if str(args.security_profile).strip():
        cmd.extend(["--security-profile", args.security_profile.strip()])
    return cmd


def main() -> int:
    args = parse_args()
    root = repo_root()

    if str(args.task_ids).strip():
        task_ids = parse_task_ids_csv(args.task_ids)
    else:
        tasks_file = Path(args.tasks_file) if str(args.tasks_file).strip() else default_tasks_file(root)
        if not tasks_file.is_absolute():
            tasks_file = (root / tasks_file).resolve()
        task_ids = load_task_ids_from_file(tasks_file, limit=max(1, args.max_tasks))

    if not task_ids:
        print("ERROR: no task ids resolved; use --task-ids or provide a valid --tasks-file.")
        return 2

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else (root / "logs" / "ci" / dt.date.today().isoformat())
    if not out_dir.is_absolute():
        out_dir = (root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = Path(args.out_json) if str(args.out_json).strip() else (out_dir / "sc-obligations-rerun-hardgate.json")
    if not out_json.is_absolute():
        out_json = (root / out_json).resolve()
    out_md = Path(args.out_md) if str(args.out_md).strip() else (out_dir / "sc-obligations-rerun-hardgate.md")
    if not out_md.is_absolute():
        out_md = (root / out_md).resolve()

    rows: list[dict[str, Any]] = []
    for round_index in range(1, args.rounds + 1):
        for task_id in task_ids:
            cmd = build_cmd(args, task_id, round_index)
            proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
            combined = "\n".join(x for x in [proc.stdout.strip(), proc.stderr.strip()] if x)
            match_status = re.search(r"status=(ok|fail)", combined)
            match_out = re.search(r"out=([^\r\n]+)", combined)
            verdict = match_status.group(1) if match_status else ("ok" if proc.returncode == 0 else "fail")
            out_path = Path(match_out.group(1).strip()) if match_out else None

            uncovered_ids: list[str] = []
            if out_path is not None:
                verdict_path = out_path / "verdict.json"
                if verdict_path.exists():
                    try:
                        verdict_obj = json.loads(verdict_path.read_text(encoding="utf-8"))
                        verdict_status = str(verdict_obj.get("status") or "").strip().lower()
                        if verdict_status in {"ok", "fail"}:
                            verdict = verdict_status
                        uncovered_ids = [str(x) for x in (verdict_obj.get("uncovered_obligation_ids") or [])]
                    except Exception:
                        pass

            row = {
                "round": round_index,
                "task_id": task_id,
                "verdict": verdict,
                "uncovered_ids": uncovered_ids,
                "return_code": proc.returncode,
            }
            rows.append(row)
            print(f"T{task_id} r{round_index}: {verdict}, uncovered={uncovered_ids}")

    stats: dict[int, dict[str, Any]] = {}
    for task_id in task_ids:
        verdict_sequence = [str(r["verdict"]) for r in rows if int(r["task_id"]) == task_id]
        uncovered_sequence = [list(r["uncovered_ids"]) for r in rows if int(r["task_id"]) == task_id]
        counts = Counter(verdict_sequence)
        if counts["ok"] >= 2:
            majority = "ok"
        elif counts["fail"] >= 2:
            majority = "fail"
        else:
            majority = "unknown"
        verdict_jitter = len(set(verdict_sequence)) > 1
        uncovered_jitter = len(set(tuple(x) for x in uncovered_sequence)) > 1

        if majority == "ok" and not verdict_jitter:
            stability = "stable_ok"
        elif majority == "fail" and not verdict_jitter:
            stability = "stable_fail"
        elif majority == "ok" and verdict_jitter:
            stability = "jitter_ok_majority"
        elif majority == "fail" and verdict_jitter:
            stability = "jitter_fail_majority"
        else:
            stability = "unknown"

        stats[task_id] = {
            "verdict_sequence": verdict_sequence,
            "uncovered_sequence": uncovered_sequence,
            "majority": majority,
            "stability": stability,
            "verdict_jitter": verdict_jitter,
            "uncovered_jitter": uncovered_jitter,
        }

    payload: dict[str, Any] = {
        "meta": {
            "date": dt.date.today().isoformat(),
            "tasks": task_ids,
            "rounds": args.rounds,
            "phase": "hardgate-round3",
            "delivery_profile": args.delivery_profile.strip() or None,
            "security_profile": args.security_profile.strip() or None,
        },
        "rows": rows,
        "task_stats": stats,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# obligations rerun hardgate", ""]
    for task_id in task_ids:
        item = stats[task_id]
        lines.append(
            f"- T{task_id}: stability={item['stability']}, majority={item['majority']}, "
            f"verdict_seq={item['verdict_sequence']}, uncovered_seq={item['uncovered_sequence']}"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"WROTE {out_json}")
    print(f"WROTE {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
