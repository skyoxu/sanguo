"""Deterministic repository knowledge catalog builder for newrouge."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any

DOMAINS = ("toolchain", "game-design", "game-runtime", "delivery")
ADR_ID = re.compile(r"ADR-\d{4}")
HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
STATUS = re.compile(r"^(?:-\s*)?Status\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

ROOT_EXACT_SOURCES = {
    "AGENTS.md",
    "README.md",
    "workflow.md",
    "DELIVERY_PROFILE.md",
    "docs/PROJECT_DOCUMENTATION_INDEX.md",
    "docs/testing-framework.md",
    "docs/architecture/ADR_INDEX_GODOT.md",
    ".taskmaster/docs/prd.txt",
}

SOURCE_PREFIXES = (
    "docs/knowledge/catalog/",
    "docs/planning/semantic-topology/",
    ".agents/skills/",
    "docs/agents/",
    "docs/prd/",
    "docs/gdd/",
    "docs/game-type-guides/",
    "docs/adr/",
    "docs/architecture/base/",
    "docs/architecture/overlays/",
    "docs/workflows/",
    "Game.Core/Contracts/",
    ".taskmaster/tasks/",
    "execution-plans/",
    "decision-logs/",
)

TEXT_SUFFIXES = {".md", ".json", ".txt", ".cs"}
MAX_SOURCE_BYTES = 4 * 1024 * 1024


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def prefixed_sha256(value: bytes) -> str:
    return "sha256:" + sha256_bytes(value)


def normalize_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("invalid_repository_path")
    return path.as_posix()


class GitSnapshot:
    def __init__(self, root: Path, authority_ref: str = "refs/heads/main") -> None:
        self.root = root.resolve()
        self.authority_ref = authority_ref
        self.commit = self._git_text("rev-parse", authority_ref).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", self.commit):
            raise ValueError("invalid_authority_commit")
        paths = self._git_text("ls-tree", "-r", "--name-only", self.commit).splitlines()
        self.paths = tuple(sorted(normalize_path(path) for path in paths if path.strip()))
        self._cache: dict[str, bytes] = {}

    def _git_text(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args],
            text=True,
            encoding="utf-8",
        )

    def contains(self, path: str) -> bool:
        return normalize_path(path) in self.paths

    def read_bytes(self, path: str) -> bytes:
        path = normalize_path(path)
        if path not in self._cache:
            self._cache[path] = subprocess.check_output(
                ["git", "-C", str(self.root), "show", f"{self.commit}:{path}"]
            )
        return self._cache[path]

    def read_text(self, path: str) -> str:
        return self.read_bytes(path).decode("utf-8-sig")

    def digest(self, path: str) -> str:
        return sha256_bytes(self.read_bytes(path))


class LocalMainSnapshot(GitSnapshot):
    """Read-only view of the local main ref without checkout or worktree creation."""
    def __init__(self, root: Path, authority_ref: str = "refs/heads/main"):
        self.root = root.resolve()
        self.authority_ref = authority_ref
        self.commit = self._git_text("rev-parse", "--verify", authority_ref).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", self.commit):
            raise ValueError("invalid_authority_commit")
        paths = self._git_text("ls-tree", "-r", "-z", "--name-only", self.commit).split('\0')
        self.paths = tuple(sorted(normalize_path(path) for path in paths if path.strip()))
        self._cache: dict[str, bytes] = {}

    def read_bytes(self, path: str) -> bytes:
        path = normalize_path(path)
        if path not in self._cache:
            self._cache[path] = subprocess.check_output(
                ["git", "-C", str(self.root), "show", f"{self.commit}:{path}"]
            )
        return self._cache[path]


class DirectorySnapshot(GitSnapshot):
    """Read-only bounded view used when the input directory is not a Git checkout."""
    def __init__(self, root: Path, selected: list[str]):
        self.root = root.resolve()
        self.authority_ref = 'local-directory'
        self._cache = {}
        for relative in selected:
            entry = self.root / normalize_path(relative)
            for path in ([entry] if entry.is_file() else entry.rglob('*')):
                if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                    raise ValueError('Symlink source is not supported')
                if not path.is_file():
                    continue
                if path.stat().st_size > MAX_SOURCE_BYTES:
                    continue
                path.resolve().relative_to(self.root)
                name = path.relative_to(self.root).as_posix()
                if any(part in {'.git', 'logs'} for part in Path(name).parts):
                    continue
                if path.suffix.lower() in {'.md', '.txt', '.json', '.cs', '.gd', '.tscn', '.tres',
                        '.cfg', '.ini', '.csv', '.yaml', '.yml', '.png', '.jpg', '.jpeg', '.svg',
                        '.webp', '.ogg', '.wav', '.mp3', '.ttf', '.otf', '.glb'}:
                    self._cache[name] = path.read_bytes()
        self.paths = tuple(sorted(self._cache))
        self.commit = 'directory:' + sha256_bytes(canonical_bytes({p: sha256_bytes(self._cache[p]) for p in self.paths}))

    def read_bytes(self, path: str) -> bytes:
        path = normalize_path(path)
        if path not in self.paths: raise FileNotFoundError(path)
        if path not in self._cache: self._cache[path] = (self.root / Path(*path.split('/'))).read_bytes()
        return self._cache[path]


def _excluded(path: str, exclusions: dict[str, Any]) -> bool:
    path = normalize_path(path)
    for rule in exclusions.get("rules", []):
        if not isinstance(rule, dict) or rule.get("disposition") != "excluded":
            continue
        prefix = rule.get("path_prefix")
        pattern = rule.get("path_pattern")
        if isinstance(prefix, str):
            normalized = normalize_path(prefix).rstrip("/")
            if path == normalized or path.startswith(normalized + "/"):
                return True
        if isinstance(pattern, str) and fnmatchcase(path, pattern):
            return True
    return False


def _title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return fallback


def _anchors(content: str, fallback: str) -> list[dict[str, Any]]:
    lines = content.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines, 1):
        match = HEADING.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    if not headings:
        return [{"anchor": fallback, "line_start": 1, "line_end": max(1, len(lines))}]
    result: list[dict[str, Any]] = []
    for pos, (start, level, name) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[pos + 1 :]:
            if next_level <= level:
                end = next_start - 1
                break
        result.append({"anchor": name, "line_start": start, "line_end": max(start, end)})
    return result


def _json_id_line(content: str, field: str, value: str) -> int:
    quoted = json.dumps(str(value), ensure_ascii=False)
    marker = f'"{field}"'
    for index, line in enumerate(content.splitlines(), 1):
        if marker in line and quoted in line:
            return index
    return 1


def _topology_nodes(path: str, content: str) -> list[dict[str, Any]]:
    if not path.startswith("docs/planning/semantic-topology/") or "/schemas/" in path:
        return []
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(document, dict):
        return []

    specs = {
        "source-blocks.v1.json": ("source_block", "blocks", "block_id"),
        "semantic-requirements.v1.json": ("requirement", "requirements", "requirement_id"),
        "capabilities.v1.json": ("capability", "capabilities", "capability_id"),
    }
    name = PurePosixPath(path).name
    if name not in specs:
        return []
    node_type, list_key, id_key = specs[name]
    rows = document.get(list_key, [])
    if not isinstance(rows, list):
        return []

    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(id_key), str) or not row[id_key]:
            continue
        node_id = row[id_key]
        line = _json_id_line(content, id_key, node_id)
        searchable = " ".join(
            str(row.get(key, ""))
            for key in ("statement", "title", "description", "kind", "source_path")
        ).strip()
        node = {
            "node_type": node_type,
            "node_id": node_id,
            "line_start": line,
            "line_end": line,
            "search_text": searchable,
            "related_nodes": [],
            "related_task_ids": [],
        }
        if node_type == "source_block":
            node["authority_sources"] = [{
                "source_block_id": node_id,
                "path": row.get("source_path"),
                "source_sha256": row.get("source_sha256") or row.get("source_file_sha256"),
                "line_start": row.get("line_start"),
                "line_end": row.get("line_end"),
            }]
        elif node_type == "requirement":
            node["source_block_ids"] = [
                str(value) for value in row.get("source_block_ids", [])
                if value is not None
            ]
            node["capability_ids"] = [
                str(value) for value in row.get("capability_ids", [])
                if value is not None
            ]
        elif node_type == "capability":
            node["requirement_ids"] = [
                str(value) for value in row.get("requirement_ids", row.get("covers", []))
                if value is not None
            ]
        result.append(node)
    return result


def _enrich_topology_nodes(modules: list[dict[str, Any]]) -> None:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    module_by_path = {module["source_path"]: module for module in modules}
    for module in modules:
        nodes = _topology_nodes(module["source_path"], module["content"])
        if nodes:
            module["topology_nodes"] = nodes
            for node in nodes:
                lookup[(node["node_type"], node["node_id"])] = node

    edges_module = module_by_path.get(
        "docs/planning/semantic-topology/topology-edges.v1.json"
    )
    edges: list[dict[str, Any]] = []
    if edges_module:
        try:
            document = json.loads(edges_module["content"])
            if isinstance(document, dict) and isinstance(document.get("edges"), list):
                edges = [edge for edge in document["edges"] if isinstance(edge, dict)]
        except json.JSONDecodeError:
            edges = []

    for edge in edges:
        source_type = str(edge.get("source_type", ""))
        source_id = str(edge.get("source_id", ""))
        target_type = str(edge.get("target_type", ""))
        target_id = str(edge.get("target_id", ""))
        relation = str(edge.get("relation", ""))
        source = lookup.get((source_type, source_id))
        target = lookup.get((target_type, target_id))
        if source is not None and target_id:
            source["related_nodes"].append({
                "node_type": target_type, "node_id": target_id,
                "relation": relation, "direction": "out",
            })
            if target_type == "task" and target_id not in source["related_task_ids"]:
                source["related_task_ids"].append(target_id)
        if target is not None and source_id:
            target["related_nodes"].append({
                "node_type": source_type, "node_id": source_id,
                "relation": relation, "direction": "in",
            })
            if source_type == "task" and source_id not in target["related_task_ids"]:
                target["related_task_ids"].append(source_id)

    # Resolve authority sources before capability rollups so file ordering cannot affect output.
    for (node_type, _), node in lookup.items():
        if node_type != "requirement":
            continue
        authority_sources = []
        for block_id in node.get("source_block_ids", []):
            block = lookup.get(("source_block", block_id))
            if block:
                authority_sources.extend(block.get("authority_sources", []))
        node["authority_sources"] = authority_sources

    for (node_type, _), node in lookup.items():
        if node_type == "requirement":
            capability_ids = set(node.get("capability_ids", []))
            capability_ids.update(
                str(item.get("node_id"))
                for item in node.get("related_nodes", [])
                if item.get("node_type") == "capability" and item.get("node_id")
            )
            for capability_id in sorted(capability_ids):
                capability = lookup.get(("capability", capability_id))
                if capability:
                    for task_id in capability.get("related_task_ids", []):
                        if task_id not in node["related_task_ids"]:
                            node["related_task_ids"].append(task_id)
        elif node_type == "capability":
            authority_sources = []
            for requirement_id in node.get("requirement_ids", []):
                requirement = lookup.get(("requirement", requirement_id))
                if requirement:
                    authority_sources.extend(requirement.get("authority_sources", []))
            node["authority_sources"] = authority_sources

    for module in modules:
        for node in module.get("topology_nodes", []):
            node["related_task_ids"].sort()
            node["related_nodes"] = sorted(
                node["related_nodes"],
                key=lambda item: (
                    item.get("node_type", ""), item.get("node_id", ""),
                    item.get("direction", ""), item.get("relation", ""),
                ),
            )


def _status(path: str, content: str) -> tuple[str, bool]:
    if path.startswith("docs/planning/semantic-topology/schemas/"):
        return "active", False
    if path.startswith("docs/adr/") and "/addenda/" not in path:
        match = STATUS.search(content)
        raw = match.group(1).strip().casefold() if match else "unmarked"
        if raw == "accepted":
            return "active", True
        if raw == "proposed":
            return "conditional", True
        if raw == "superseded":
            return "historical", True
        return "excluded", False
    if path.startswith("execution-plans/"):
        match = STATUS.search(content)
        raw = match.group(1).strip().casefold().replace("_", "-") if match else "active"
        if raw in {"done", "completed", "implementation-complete", "acceptance-passed", "archived"}:
            return "historical", True
        if raw in {"draft", "proposed", "paused", "plan-ready"}:
            return "conditional", True
    return "active", True


def _classification(path: str) -> tuple[str, tuple[str, ...], str, str]:
    if path in {
        "AGENTS.md",
        "workflow.md",
        "DELIVERY_PROFILE.md",
        "docs/testing-framework.md",
        "docs/PROJECT_DOCUMENTATION_INDEX.md",
    } or path.startswith((".agents/skills/", "docs/agents/", "docs/workflows/")):
        return "toolchain", ("delivery", "game-runtime"), "toolchain-document", "repository-authority"
    if path.startswith("docs/knowledge/catalog/"):
        return "game-runtime", ("game-design", "delivery"), "resource-knowledge", "resource-guide"
    if path.startswith("docs/planning/semantic-topology/"):
        return "game-design", ("delivery", "game-runtime"), "semantic-topology", "derived-planning-topology"
    if path == "README.md":
        return "game-design", ("toolchain", "delivery"), "repository-overview", "repository-overview"
    if path.startswith(("docs/prd/", "docs/gdd/", "docs/game-type-guides/")) or path == ".taskmaster/docs/prd.txt":
        return "game-design", ("game-runtime", "delivery"), "game-design", "product-authority"
    if path == "docs/architecture/ADR_INDEX_GODOT.md":
        return "game-runtime", ("toolchain", "delivery"), "architecture-index", "navigation-authority"
    if path.startswith(("docs/adr/", "docs/architecture/", "Game.Core/Contracts/")):
        return "game-runtime", ("game-design", "toolchain"), "architecture", "architecture-authority"
    if path.startswith((".taskmaster/tasks/", "execution-plans/", "decision-logs/")):
        return "delivery", ("toolchain", "game-design", "game-runtime"), "delivery-state", "delivery-authority"
    raise ValueError("unclassified_path")


def _visibility(primary: str, dependencies: tuple[str, ...]) -> dict[str, str]:
    return {
        domain: "active" if domain == primary else "dependency" if domain in dependencies else "excluded"
        for domain in DOMAINS
    }


def _eligible_source(path: str) -> bool:
    if path in ROOT_EXACT_SOURCES:
        return True
    return path.startswith(SOURCE_PREFIXES) and PurePosixPath(path).suffix.casefold() in TEXT_SUFFIXES


def _consumer_ids(primary: str) -> list[str]:
    if primary == "delivery":
        return ["repository-session", "chapter5", "chapter6", "review"]
    return ["repository-session", "chapter4", "chapter5", "chapter6", "review"]


def build_layers(
    snapshot: GitSnapshot,
    exclusions: dict[str, Any],
    policies: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    adr_ids: dict[str, str] = {}

    for path in snapshot.paths:
        if not _eligible_source(path) or _excluded(path, exclusions):
            continue
        try:
            content = snapshot.read_text(path)
        except UnicodeDecodeError:
            continue

        primary, deps, kind, role = _classification(path)
        status, semantic_eligible = _status(path, content)
        module_id = "source." + re.sub(r"[^a-z0-9]+", ".", path.casefold()).strip(".")
        adr_match = ADR_ID.search(PurePosixPath(path).name)
        if adr_match and path.startswith("docs/adr/") and "/addenda/" not in path:
            module_id = "adr." + adr_match.group(0)
            adr_ids[adr_match.group(0)] = module_id

        title = _title(content, PurePosixPath(path).name)
        digest = snapshot.digest(path)
        modules.append(
            {
                "module_id": module_id,
                "kind": kind,
                "title": title,
                "primary_domain": primary,
                "visibility": _visibility(primary, deps),
                "lifecycle": "repository-source",
                "enforcement_level": "E1",
                "authority_class": "derived-cache",
                "source_role": role,
                "status": status,
                "semantic_eligible": semantic_eligible,
                "source_path": path,
                "source_sha256": digest,
                "anchor": title,
                "anchors": _anchors(content, title)
                if path.endswith(".md")
                else [
                    {
                        "anchor": "document",
                        "line_start": 1,
                        "line_end": max(1, len(content.splitlines())),
                    }
                ],
                "consumer_ids": _consumer_ids(primary),
                "relations": [],
                "content": content,
            }
        )
        sources.append({"path": path, "sha256": digest, "source_role": role})

    _enrich_topology_nodes(modules)

    by_id = {module["module_id"]: module for module in modules}
    for module in modules:
        own = module["module_id"].removeprefix("adr.") if module["module_id"].startswith("adr.") else None
        refs = sorted(set(ADR_ID.findall(module["content"])))
        module["relations"] = [
            {"type": "references", "target": adr_ids[ref]}
            for ref in refs
            if ref != own and ref in adr_ids and adr_ids[ref] in by_id
        ]

    sources.sort(key=lambda item: item["path"])
    modules.sort(key=lambda item: item["module_id"])
    snapshot_doc = {
        "schema_version": "newrouge.repository-source-snapshot.v1",
        "snapshot_id": sha256_bytes(
            (
                snapshot.authority_ref
                + "\0"
                + snapshot.commit
                + "\0"
                + json.dumps(sources, sort_keys=True)
            ).encode("utf-8")
        ),
        "ref": snapshot.authority_ref,
        "commit": snapshot.commit,
        "sources": sources,
    }
    catalog = {
        "schema_version": "newrouge.repository-knowledge-catalog.v1",
        "source_snapshot": snapshot_doc,
        "domains": list(DOMAINS),
        "modules": modules,
    }

    projection_items = []
    for policy in policies.get("policies", []):
        consumer = policy.get("consumer")
        allowed_domains = set(policy.get("domains", []))
        allowed_statuses = set(policy.get("statuses", []))
        allowed_visibility = set(policy.get("visibility", []))
        ids = []
        for module in modules:
            if (
                consumer not in module.get("consumer_ids", [])
                or module.get("status") not in allowed_statuses
                or not module.get("semantic_eligible", True)
            ):
                continue
            if not any(
                module.get("visibility", {}).get(domain) in allowed_visibility
                for domain in allowed_domains
            ):
                continue
            path = module["source_path"]
            if path not in policy.get("exact_paths", []) and not any(
                path.startswith(prefix) for prefix in policy.get("path_prefixes", [])
            ):
                continue
            ids.append(module["module_id"])
        projection_items.append(
            {"consumer": consumer, "eligible_module_ids": sorted(ids)}
        )

    projections = {
        "schema_version": "newrouge.knowledge-consumer-projections.v1",
        "source_snapshot_id": snapshot_doc["snapshot_id"],
        "catalog_sha256": prefixed_sha256(canonical_bytes(catalog)),
        "policy_revision": policies["policy_revision"],
        "policy_sha256": prefixed_sha256(canonical_bytes(policies)),
        "projections": projection_items,
    }
    return snapshot_doc, catalog, projections
