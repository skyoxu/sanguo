"""Read-only producer for SHA-bound knowledge consumption evidence."""
from __future__ import annotations
import hashlib, json, subprocess
import argparse
from pathlib import Path
from typing import Any

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def produce_binding(root: Path, bundle: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    """Reread accepted candidate sources at the bundle revision; never mutates authority."""
    if bundle.get("status") != "shadow_ready" or bundle.get("freeze_state") != "unfrozen":
        raise ValueError("candidate_bundle_not_ready")
    snap = bundle.get("snapshot") or {}; revision = snap.get("commit")
    if not isinstance(revision, str) or not revision:
        raise ValueError("snapshot_invalid")
    if decisions.get("request_id") != bundle.get("request_id"):
        raise ValueError("decision_set_binding_mismatch")
    accepted = decisions.get("accepted", [])
    if not accepted and isinstance(decisions.get("decisions"), list):
        accepted = [item.get("candidate", {}) for item in decisions["decisions"] if isinstance(item, dict) and item.get("decision") == "accepted"]
    if not isinstance(accepted, list): raise ValueError("decision_set_invalid")
    candidate_paths = {str(c.get("path")) for c in bundle.get("candidates", []) if isinstance(c, dict) and c.get("path")}
    evidence = []
    for item in accepted:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("decision_set_invalid")
        path = item["path"].replace("\\", "/")
        if candidate_paths and path not in candidate_paths:
            raise ValueError("decision_not_in_bundle")
        try:
            raw = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{path}"], capture_output=True, check=True, timeout=30).stdout
        except Exception as exc:
            raise ValueError("source_reread_failed") from exc
        evidence.append({"path": path, "sha256": _sha(raw), "decision": "accepted"})
    evidence.sort(key=lambda x: x["path"].encode("utf-8"))
    return {"schema_version":"newrouge.knowledge-binding-evidence.v1", "repository_revision":revision, "request_id":bundle["request_id"], "source_bundle_sha256":"sha256:" + _sha(json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()), "evidence":evidence}

def validate_binding_evidence(root: Path, bundle: dict[str, Any], evidence: dict[str, Any]) -> None:
    if evidence.get("schema_version") != "newrouge.knowledge-binding-evidence.v1": raise ValueError("binding_schema_invalid")
    if evidence.get("request_id") != bundle.get("request_id"): raise ValueError("binding_request_mismatch")
    revision = evidence.get("repository_revision")
    if not isinstance(revision, str) or subprocess.run(["git", "-C", str(root), "cat-file", "-e", revision], capture_output=True).returncode != 0: raise ValueError("binding_revision_invalid")
    for item in evidence.get("evidence", []):
        path, expected = item.get("path"), item.get("sha256")
        if not isinstance(path, str) or not isinstance(expected, str): raise ValueError("binding_entry_invalid")
        try: raw = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{path}"], capture_output=True, check=True, timeout=30).stdout
        except Exception as exc: raise ValueError("source_reread_failed") from exc
        if _sha(raw) != expected: raise ValueError("binding_source_hash_mismatch")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(); root = Path(__file__).resolve().parents[2]
    try:
        result = produce_binding(root, json.loads(Path(args.bundle).read_text(encoding="utf-8")), json.loads(Path(args.decisions).read_text(encoding="utf-8")))
        Path(args.output).parent.mkdir(parents=True, exist_ok=True); Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        return 0
    except (OSError, ValueError, json.JSONDecodeError):
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
