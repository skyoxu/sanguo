import argparse
import copy
import datetime as dt
import json
import subprocess
from pathlib import Path


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_from_head(repo_rel_path: str) -> object:
    content = subprocess.check_output(
        ["git", "show", f"HEAD:{repo_rel_path}"],
        text=True,
        encoding="utf-8",
    )
    return json.loads(content)


def _index_by_task_id(tasks: list[dict]) -> dict[int, dict]:
    indexed: dict[int, dict] = {}
    for task in tasks:
        task_id = task.get("taskmaster_id")
        if isinstance(task_id, int):
            indexed[task_id] = task
    return indexed


def _ensure_logs_dir() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path("logs") / "ci" / date / "restore-tasks-from-head"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore selected task entries in JSON files to HEAD.")
    parser.add_argument("--task-ids", required=True, help="Comma-separated taskmaster_id list.")
    parser.add_argument(
        "--paths",
        default=".taskmaster/tasks/tasks_back.json,.taskmaster/tasks/tasks_gameplay.json",
        help="Comma-separated repo-relative JSON paths to restore in.",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to disk.")
    args = parser.parse_args()

    task_ids = [int(x.strip()) for x in args.task_ids.split(",") if x.strip()]
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]

    out_dir = _ensure_logs_dir()
    summary = {"task_ids": task_ids, "paths": paths, "changed": [], "skipped": [], "errors": []}

    for repo_rel in paths:
        try:
            head_data = _load_from_head(repo_rel)
            wt_path = Path(repo_rel)
            wt_data = _load_json(wt_path)
            if not isinstance(head_data, list) or not isinstance(wt_data, list):
                raise ValueError("Expected JSON list at root.")

            head_index = _index_by_task_id(head_data)
            changed_any = False
            wt_by_id = _index_by_task_id(wt_data)

            for task_id in task_ids:
                head_task = head_index.get(task_id)
                wt_task = wt_by_id.get(task_id)
                if head_task is None:
                    summary["skipped"].append({"path": repo_rel, "task_id": task_id, "reason": "missing_in_head"})
                    continue
                if wt_task is None:
                    summary["skipped"].append({"path": repo_rel, "task_id": task_id, "reason": "missing_in_worktree"})
                    continue
                if wt_task == head_task:
                    summary["skipped"].append({"path": repo_rel, "task_id": task_id, "reason": "already_matches_head"})
                    continue

                # Replace the dict in-place by locating its index in the list.
                replaced = False
                for i, t in enumerate(wt_data):
                    if t.get("taskmaster_id") == task_id:
                        wt_data[i] = copy.deepcopy(head_task)
                        replaced = True
                        break
                if not replaced:
                    summary["errors"].append({"path": repo_rel, "task_id": task_id, "reason": "index_not_found"})
                    continue

                changed_any = True
                summary["changed"].append({"path": repo_rel, "task_id": task_id})

            if changed_any and args.write:
                _write_json(wt_path, wt_data)
        except Exception as e:  # noqa: BLE001
            summary["errors"].append({"path": repo_rel, "reason": str(e)})

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if summary["errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

