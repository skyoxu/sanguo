from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


POLICY_REVISION = "newrouge-knowledge-consumer-policies.v1"


class FreezeBlocked(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _prefixed_sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent, suffix=".tmp"
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _git_text(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise FreezeBlocked("git_authority_unavailable")
    return completed.stdout.strip()


def _git_blob(root: Path, commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise FreezeBlocked("source_reread_failed")
    return completed.stdout


def _policy(root: Path, consumer: str, policy_revision: str) -> dict[str, Any]:
    registry = json.loads(
        (root / "knowledge/policies/consumer-policies.v1.json").read_text(encoding="utf-8")
    )
    if registry.get("policy_revision") != policy_revision:
        raise FreezeBlocked("policy_revision_mismatch")
    policy = next(
        (item for item in registry.get("policies", []) if isinstance(item, dict) and item.get("consumer") == consumer),
        None,
    )
    if policy is None:
        raise FreezeBlocked("consumer_policy_missing")
    return policy


def _publication_lineage(root: Path, commit: str) -> tuple[str, str]:
    pointer = json.loads((root / "knowledge/indexes/current.json").read_text(encoding="utf-8"))
    if pointer.get("authority_ref") != "refs/heads/main" or pointer.get("main_commit") != commit:
        raise FreezeBlocked("publication_authority_mismatch")
    generation = str(pointer.get("generation_id") or "")
    generation_sha = str(pointer.get("generation_sha256") or "")
    if not generation or not generation_sha.startswith("sha256:"):
        raise FreezeBlocked("publication_lineage_missing")
    return generation, generation_sha


def freeze(
    root: Path,
    *,
    bundle: dict[str, Any],
    decision_set: dict[str, Any],
    task_id: str | None = None,
) -> dict[str, Any]:
    if (
        bundle.get("schema_version") != "newrouge.knowledge-context-candidates.v1"
        or bundle.get("mode") != "shadow"
        or bundle.get("status") != "shadow_ready"
        or bundle.get("freeze_state") != "unfrozen"
    ):
        raise FreezeBlocked("candidate_bundle_not_freezable")

    consumer = bundle.get("consumer")
    request_id = bundle.get("request_id")
    snapshot = bundle.get("snapshot")
    policy_revision = bundle.get("policy_revision")
    if not isinstance(consumer, str) or not isinstance(request_id, str) or not isinstance(snapshot, dict):
        raise FreezeBlocked("candidate_bundle_invalid")
    if policy_revision != POLICY_REVISION:
        raise FreezeBlocked("policy_revision_mismatch")

    source_bundle_sha = _prefixed_sha(bundle)
    if (
        decision_set.get("schema_version") != "newrouge.knowledge-consumption-decision-set.v1"
        or decision_set.get("consumer") != consumer
        or decision_set.get("request_id") != request_id
        or decision_set.get("source_bundle_sha256") != source_bundle_sha
    ):
        raise FreezeBlocked("decision_set_binding_mismatch")

    ref = snapshot.get("ref")
    commit = snapshot.get("commit")
    if not isinstance(ref, str) or not isinstance(commit, str):
        raise FreezeBlocked("snapshot_invalid")
    if _git_text(root, "rev-parse", ref) != commit:
        raise FreezeBlocked("authority_ref_moved")
    publication_generation, publication_sha256 = _publication_lineage(root, commit)

    policy = _policy(root, consumer, policy_revision)
    if consumer != "review" and (not isinstance(task_id, str) or not task_id.strip()):
        raise FreezeBlocked("task_id_missing")
    required = set(policy.get("required_context_classes", []))
    optional = set(policy.get("optional_context_classes", []))
    allowed_classes = required | optional
    freeze_point = policy.get("freeze_point")
    if not isinstance(freeze_point, str) or not freeze_point:
        raise FreezeBlocked("freeze_point_missing")

    candidates = {
        (str(item.get("module_id", "")), str(item.get("path", ""))): item
        for item in bundle.get("candidates", [])
        if isinstance(item, dict)
    }
    if not candidates:
        raise FreezeBlocked("candidate_set_empty")

    decisions = decision_set.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise FreezeBlocked("decision_set_empty")

    seen: set[tuple[str, str]] = set()
    accepted_sources: list[dict[str, Any]] = []
    satisfied: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise FreezeBlocked("decision_invalid")
        if (
            decision.get("schema_version") != "newrouge.knowledge-consumption-decision.v1"
            or decision.get("consumer") != consumer
            or decision.get("request_id") != request_id
        ):
            raise FreezeBlocked("decision_binding_mismatch")
        candidate_ref = decision.get("candidate")
        if not isinstance(candidate_ref, dict):
            raise FreezeBlocked("decision_candidate_invalid")
        key = (str(candidate_ref.get("module_id", "")), str(candidate_ref.get("path", "")))
        if key in seen:
            raise FreezeBlocked("duplicate_candidate_decision")
        seen.add(key)
        candidate = candidates.get(key)
        if candidate is None:
            raise FreezeBlocked("decision_candidate_not_in_bundle")

        source_sha = decision.get("source_sha256")
        if source_sha != candidate.get("source_sha256"):
            raise FreezeBlocked("decision_source_hash_mismatch")
        blob_sha = hashlib.sha256(_git_blob(root, commit, key[1])).hexdigest()
        if blob_sha != source_sha:
            raise FreezeBlocked("source_reread_hash_mismatch")

        classes = decision.get("satisfies")
        if not isinstance(classes, list) or any(not isinstance(value, str) for value in classes):
            raise FreezeBlocked("decision_context_classes_invalid")
        if not set(classes).issubset(allowed_classes):
            raise FreezeBlocked("decision_context_class_unknown")

        reason = decision.get("reason")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise FreezeBlocked("decision_reason_invalid")
        disposition = decision.get("decision")
        if disposition == "rejected":
            if classes:
                raise FreezeBlocked("rejected_candidate_cannot_satisfy")
            continue
        if disposition != "accepted":
            raise FreezeBlocked("decision_disposition_invalid")
        accepted_sources.append(
            {
                "module_id": key[0],
                "path": key[1],
                "source_sha256": source_sha,
                "reason": reason.strip(),
                "satisfies": sorted(set(classes)),
            }
        )
        satisfied.update(classes)

    missing = sorted(required - satisfied)
    if missing:
        raise FreezeBlocked("required_context_incomplete:" + ",".join(missing))
    if not accepted_sources:
        raise FreezeBlocked("no_accepted_sources")

    accepted_sources.sort(key=lambda item: (item["path"], item["module_id"]))
    basis = {
        "consumer": consumer,
        "request_id": request_id,
        "freeze_point": freeze_point,
        "snapshot": {"ref": ref, "commit": commit},
        "policy_revision": policy_revision,
        "source_bundle_sha256": source_bundle_sha,
        "decision_set_sha256": _prefixed_sha(decision_set),
        "task_id": task_id if consumer != "review" else None,
        "publication_generation": publication_generation,
        "publication_sha256": publication_sha256.removeprefix("sha256:"),
        "required_context_classes": sorted(required),
        "satisfied_context_classes": sorted(satisfied),
        "accepted_sources": accepted_sources,
    }
    return {
        "schema_version": "newrouge.knowledge-frozen-context.v1",
        "context_id": _prefixed_sha(basis),
        "freeze_state": "frozen",
        **basis,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze an explicitly accepted, source-verified newrouge knowledge context."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task-id")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    bundle_path = args.bundle if args.bundle.is_absolute() else root / args.bundle
    decision_path = args.decisions if args.decisions.is_absolute() else root / args.decisions
    try:
        frozen = freeze(
            root,
            bundle=json.loads(bundle_path.read_text(encoding="utf-8")),
            decision_set=json.loads(decision_path.read_text(encoding="utf-8")),
            task_id=args.task_id,
        )
    except (OSError, json.JSONDecodeError, FreezeBlocked) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "newrouge.knowledge-freeze-result.v1",
                    "status": "blocked",
                    "reason": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        _atomic_json(output, frozen)
    print(json.dumps(frozen, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
