#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _artifact_schema import (  # noqa: E402
    ArtifactSchemaError,
    validate_local_hard_checks_execution_context_payload,
    validate_local_hard_checks_latest_index_payload,
    validate_local_hard_checks_repair_guide_payload,
    validate_pipeline_execution_context_payload,
    validate_pipeline_latest_index_payload,
    validate_pipeline_repair_guide_payload,
)
from _failure_taxonomy import classify_run_failure  # noqa: E402
from _summary_schema import (  # noqa: E402
    SummarySchemaError,
    validate_local_hard_checks_summary,
    validate_pipeline_summary,
)


def _to_posix(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _resolve_path(root: Path, raw_value: Any) -> Path | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _bundle_root_from_latest(latest_path: Path) -> Path | None:
    parts = latest_path.resolve().parts
    lower_parts = [part.lower() for part in parts]
    for index in range(len(lower_parts) - 1):
        if lower_parts[index] == "logs" and lower_parts[index + 1] == "ci" and index > 0:
            return Path(*parts[:index]).resolve()
    return None


def _detect_kind(*, latest_path: Path, latest_payload: dict[str, Any], requested_kind: str) -> str:
    kind = str(requested_kind or "").strip().lower()
    if kind in {"pipeline", "local-hard-checks"}:
        return kind
    if str(latest_payload.get("cmd") or "").strip() == "local-hard-checks":
        return "local-hard-checks"
    if "out_dir" in latest_payload and "latest_out_dir" not in latest_payload:
        return "local-hard-checks"
    if "latest_out_dir" in latest_payload:
        return "pipeline"
    latest_name = latest_path.name.lower()
    if latest_name == "local-hard-checks-latest.json":
        return "local-hard-checks"
    return "pipeline"


def _latest_candidates(root: Path, *, kind: str, task_id: str, run_id: str) -> list[Path]:
    candidates: list[Path] = []
    ci_root = root / "logs" / "ci"
    if kind in {"", "pipeline"}:
        if task_id:
            candidates.extend(ci_root.glob(f"*/sc-review-pipeline-task-{task_id}/latest.json"))
        else:
            candidates.extend(ci_root.glob("*/sc-review-pipeline-task-*/latest.json"))
    if kind in {"", "local-hard-checks"}:
        candidates.extend(ci_root.glob("*/local-hard-checks-latest.json"))
    if run_id:
        filtered: list[Path] = []
        for path in candidates:
            try:
                payload = _load_json(path)
            except Exception:
                continue
            if str(payload.get("run_id") or "").strip() == run_id:
                filtered.append(path)
        candidates = filtered
    unique = sorted({path.resolve() for path in candidates if path.is_file()}, key=lambda item: item.stat().st_mtime, reverse=True)
    return unique


def _resolve_latest_path(root: Path, *, latest: str, kind: str, task_id: str, run_id: str) -> Path:
    explicit = str(latest or "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        return path.resolve()
    candidates = _latest_candidates(root, kind=kind, task_id=task_id, run_id=run_id)
    if not candidates:
        raise FileNotFoundError("No latest run index found. Pass --latest or provide enough filters.")
    return candidates[0]


def _validate_latest(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_latest_index_payload(payload)
        return
    validate_pipeline_latest_index_payload(payload)


def _validate_execution_context(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_execution_context_payload(payload)
        return
    validate_pipeline_execution_context_payload(payload)


def _validate_repair_guide(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_repair_guide_payload(payload)
        return
    validate_pipeline_repair_guide_payload(payload)


def _validate_summary(kind: str, payload: dict[str, Any]) -> None:
    if kind == "local-hard-checks":
        validate_local_hard_checks_summary(payload)
        return
    validate_pipeline_summary(payload)


def _default_sidecar_paths(root: Path, kind: str, out_dir: Path | None) -> dict[str, Path | None]:
    if out_dir is None:
        return {"summary": None, "execution_context": None, "repair_guide": None, "repair_guide_md": None}
    return {
        "summary": (out_dir / "summary.json").resolve(),
        "execution_context": (out_dir / "execution-context.json").resolve(),
        "repair_guide": (out_dir / "repair-guide.json").resolve(),
        "repair_guide_md": (out_dir / "repair-guide.md").resolve(),
    }


def _sidecar_paths(root: Path, kind: str, latest_payload: dict[str, Any], out_dir: Path | None) -> dict[str, Path | None]:
    defaults = _default_sidecar_paths(root, kind, out_dir)
    if kind == "local-hard-checks":
        return {
            "summary": _resolve_path(root, latest_payload.get("summary_path")) or defaults["summary"],
            "execution_context": _resolve_path(root, latest_payload.get("execution_context_path")) or defaults["execution_context"],
            "repair_guide": _resolve_path(root, latest_payload.get("repair_guide_json_path")) or defaults["repair_guide"],
            "repair_guide_md": _resolve_path(root, latest_payload.get("repair_guide_md_path")) or defaults["repair_guide_md"],
        }
    return {
        "summary": _resolve_path(root, latest_payload.get("summary_path")) or defaults["summary"],
        "execution_context": _resolve_path(root, latest_payload.get("execution_context_path")) or defaults["execution_context"],
        "repair_guide": _resolve_path(root, latest_payload.get("repair_guide_json_path")) or defaults["repair_guide"],
        "repair_guide_md": _resolve_path(root, latest_payload.get("repair_guide_md_path")) or defaults["repair_guide_md"],
    }


def _resolve_artifact_root(root: Path, latest_path: Path, latest_payload: dict[str, Any], kind: str) -> tuple[Path, Path | None]:
    out_dir_key = "out_dir" if kind == "local-hard-checks" else "latest_out_dir"
    candidate_roots = [root]
    bundle_root = _bundle_root_from_latest(latest_path)
    if bundle_root is not None and bundle_root not in candidate_roots:
        candidate_roots.append(bundle_root)

    for candidate_root in candidate_roots:
        out_dir = _resolve_path(candidate_root, latest_payload.get(out_dir_key))
        if out_dir is not None and out_dir.exists():
            return candidate_root, out_dir
    return candidate_roots[0], _resolve_path(candidate_roots[0], latest_payload.get(out_dir_key))


def _collect_sidecars(
    *,
    kind: str,
    sidecar_paths: dict[str, Path | None],
    validation_errors: list[str],
    missing_artifacts: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for key in ("summary", "execution_context", "repair_guide"):
        path = sidecar_paths.get(key)
        if path is None or not path.exists():
            missing_artifacts.append(key)
            continue
        try:
            payload = _load_json(path)
            if key == "summary":
                _validate_summary(kind, payload)
            elif key == "execution_context":
                _validate_execution_context(kind, payload)
            else:
                _validate_repair_guide(kind, payload)
            loaded[key] = payload
        except (OSError, ValueError, json.JSONDecodeError, SummarySchemaError, ArtifactSchemaError) as exc:
            validation_errors.append(f"{key}: {exc}")
    return loaded.get("summary", {}), loaded.get("execution_context", {}), loaded.get("repair_guide", {})


def inspect_run_artifacts(
    *,
    repo_root: Path,
    latest: str = "",
    kind: str = "",
    task_id: str = "",
    run_id: str = "",
) -> tuple[int, dict[str, Any]]:
    root = Path(repo_root).resolve()
    validation_errors: list[str] = []
    missing_artifacts: list[str] = []
    stale_latest = False

    latest_path = _resolve_latest_path(root, latest=latest, kind=kind, task_id=task_id, run_id=run_id)
    latest_payload: dict[str, Any] = {}
    detected_kind = str(kind or "").strip().lower() or "pipeline"
    try:
        latest_payload = _load_json(latest_path)
        detected_kind = _detect_kind(latest_path=latest_path, latest_payload=latest_payload, requested_kind=kind)
        _validate_latest(detected_kind, latest_payload)
    except FileNotFoundError:
        raise
    except (OSError, ValueError, json.JSONDecodeError, ArtifactSchemaError) as exc:
        validation_errors.append(f"latest: {exc}")

    artifact_root, out_dir = _resolve_artifact_root(root, latest_path, latest_payload, detected_kind)
    if out_dir is None or not out_dir.exists():
        stale_latest = True

    sidecar_paths = _sidecar_paths(artifact_root, detected_kind, latest_payload, out_dir)
    summary, execution_context, repair_guide = _collect_sidecars(
        kind=detected_kind,
        sidecar_paths=sidecar_paths,
        validation_errors=validation_errors,
        missing_artifacts=missing_artifacts,
    )

    latest_status = str(latest_payload.get("status") or "").strip()
    summary_status = str(summary.get("status") or latest_status or "").strip()
    repair_status = str(repair_guide.get("status") or "").strip()
    failed_step = str(summary.get("failed_step") or execution_context.get("failed_step") or repair_guide.get("failed_step") or "").strip()
    failure = classify_run_failure(
        latest_status=latest_status,
        summary_status=summary_status,
        repair_status=repair_status,
        failed_step=failed_step,
        validation_errors=validation_errors,
        missing_artifacts=missing_artifacts,
        stale_latest=stale_latest,
    )
    status = "aborted" if failure["code"] == "aborted" else ("ok" if failure["code"] == "ok" else "fail")
    payload = {
        "kind": "pipeline" if detected_kind == "pipeline" else "local-hard-checks",
        "status": status,
        "task_id": str(latest_payload.get("task_id") or summary.get("task_id") or execution_context.get("task_id") or task_id or "").strip(),
        "run_id": str(latest_payload.get("run_id") or summary.get("run_id") or execution_context.get("run_id") or run_id or "").strip(),
        "latest_status": latest_status,
        "summary_status": summary_status,
        "repair_status": repair_status or "unknown",
        "failed_step": failed_step,
        "failure": failure,
        "validation_errors": validation_errors,
        "missing_artifacts": missing_artifacts,
        "stale_latest": stale_latest,
        "paths": {
            "latest": _to_posix(root, latest_path),
            "out_dir": _to_posix(root, out_dir),
            "summary": _to_posix(root, sidecar_paths.get("summary")),
            "execution_context": _to_posix(root, sidecar_paths.get("execution_context")),
            "repair_guide": _to_posix(root, sidecar_paths.get("repair_guide")),
            "repair_guide_md": _to_posix(root, sidecar_paths.get("repair_guide_md")),
        },
    }
    return (0 if failure["code"] == "ok" else 1), payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the latest local harness run and emit a stable JSON summary.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root used to resolve relative paths.")
    parser.add_argument("--latest", default="", help="Explicit latest index path.")
    parser.add_argument("--kind", default="", choices=["", "pipeline", "local-hard-checks"], help="Expected run kind.")
    parser.add_argument("--task-id", default="", help="Task id used to resolve the latest pipeline run.")
    parser.add_argument("--run-id", default="", help="Optional run id filter when resolving latest.json automatically.")
    parser.add_argument("--out-json", default="", help="Optional file path to persist the inspection payload.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        rc, payload = inspect_run_artifacts(
            repo_root=Path(str(args.repo_root or REPO_ROOT)),
            latest=str(args.latest or "").strip(),
            kind=str(args.kind or "").strip(),
            task_id=str(args.task_id or "").strip(),
            run_id=str(args.run_id or "").strip(),
        )
    except FileNotFoundError as exc:
        print(json.dumps({"status": "fail", "failure": {"code": "artifact-missing", "message": str(exc), "severity": "hard"}}, ensure_ascii=False, indent=2))
        return 2

    out_json = str(args.out_json or "").strip()
    if out_json:
        out_path = Path(out_json)
        if not out_path.is_absolute():
            out_path = Path(str(args.repo_root or REPO_ROOT)) / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
