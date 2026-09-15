"""Conservative static Godot scene graph extraction for Project Health."""
from __future__ import annotations

import posixpath
import re
from collections import deque
from pathlib import PurePosixPath

SCENE_SUFFIX = ".tscn"
CONFIG_SUFFIXES = {".json", ".cfg", ".ini", ".csv", ".yaml", ".yml", ".tres", ".res"}
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".wav", ".ogg", ".mp3", ".ttf", ".otf"}
_PATH = re.compile(r"res://([^\"'\s)]+\.tscn)")
_RES_PATH = re.compile(r"res://([^\"'\s)]+)")
_EXT = re.compile(r'^\[ext_resource\b[^\]]*\bpath="([^"]+)"[^\]]*\bid="([^"]+)"')
_NODE = re.compile(r"^\[node\b([^\]]*)\]")
_SUB = re.compile(r'^\[sub_resource\s+type="([^"]+)"\s+id="([^"]+)"\]')


def _clean(path: str) -> str:
    return path.removeprefix("res://").replace("\\", "/")


def _resolve_target(source: str, target: str, known: set[str]) -> str:
    target = posixpath.normpath(target).lstrip("./")
    if target in known:
        return target
    parts = source.split("/")
    for index in range(len(parts) - 1, 0, -1):
        candidate = posixpath.normpath("/".join(parts[:index] + [target]))
        if candidate in known:
            return candidate
    return target


def _scene_evidence(line: str) -> tuple[str, str]:
    if re.search(r"\b(?:change_scene(?:_to_file|_to_packed)?|_?switch_to|instantiate)\s*\(", line):
        return "effective", "explicit scene switch or instantiation call"
    return "possible", "scene path literal without a statically proven trigger"


def _main_scene(project_text: str) -> str | None:
    match = re.search(r'(?:run/main_scene|application/run/main_scene)\s*=\s*"res://([^"\r\n]+)"', project_text)
    return _clean(match.group(1)) if match else None


def _parse_scene(path: str, text: str) -> tuple[dict, list[dict], list[dict]]:
    ext: dict[str, str] = {}
    nodes: list[dict] = []
    subs: list[dict] = []
    diagnostics: list[dict] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = _EXT.match(line)
        if match:
            ext[match.group(2)] = _clean(match.group(1))
            continue
        match = _SUB.match(line)
        if match:
            subs.append({"type": match.group(1), "id": match.group(2), "line": line_no})
            continue
        match = _NODE.match(line)
        if match:
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
            instance = re.search(r'instance=ExtResource\("([^"]+)"\)', match.group(1))
            node = {
                "name": attrs.get("name", ""),
                "type": attrs.get("type", "inherited"),
                "parent": attrs.get("parent", "."),
                "line": line_no,
                "instance": ext.get(instance.group(1)) if instance else None,
                "resources": [],
            }
            if instance and instance.group(1) not in ext:
                node["parse_error"] = "missing ExtResource " + instance.group(1)
                diagnostics.append({"kind": "parse_error", "scene": path, "line": line_no, "reason": node["parse_error"]})
            nodes.append(node)
            continue
        if nodes:
            nodes[-1]["resources"].extend(_clean(item.group(1)) for item in _RES_PATH.finditer(line))
            nodes[-1]["resources"].extend(
                f'SubResource({item.group(1)})' for item in re.finditer(r'SubResource\("([^"]+)"\)', line)
            )
    if not text.lstrip().startswith(("[gd_scene", "[gd_resource")):
        diagnostics.append({"kind": "parse_error", "scene": path, "line": 1, "reason": "missing gd_scene header"})
    refs = [
        {
            "source": path,
            "target": _clean(match.group(1)),
            "line": line_no,
            "kind": "packed_scene",
            "evidence_level": "effective",
            "evidence": "PackedScene reference declared in scene",
        }
        for line_no, line in enumerate(text.splitlines(), 1)
        for match in _PATH.finditer(line)
        if _clean(match.group(1)) != path
    ]
    root = next((node for node in nodes if node.get("parent") == "."), nodes[0] if nodes else {})
    scripts = sorted(value for value in ext.values() if value.endswith((".gd", ".cs")))
    result = {
        "path": path,
        "nodes": nodes,
        "external_resources": ext,
        "sub_resources": subs,
        "child_scene_references": sorted({item["target"] for item in refs}),
        "description": f"Godot {root.get('type', 'scene')} scene with {len(nodes)} nodes" + (f"; scripts: {', '.join(scripts)}" if scripts else ""),
    }
    if diagnostics:
        result["parse_error"] = "; ".join(item["reason"] for item in diagnostics)
    return result, refs, diagnostics


def _dedupe_edges(edges: list[dict]) -> list[dict]:
    result: dict[tuple, dict] = {}
    for edge in edges:
        key = (edge.get("source"), edge.get("target"), edge.get("kind"), edge.get("event"))
        previous = result.get(key)
        if previous is None or (edge.get("evidence_level") == "effective" and previous.get("evidence_level") != "effective"):
            result[key] = edge
    return sorted(result.values(), key=lambda item: (str(item.get("source")), str(item.get("target")), str(item.get("kind"))))


def build_scene_graph(
    sources: dict[str, str],
    task_details: list[dict] | None = None,
    known_paths: list[str] | tuple[str, ...] | None = None,
) -> dict:
    normalized = {path.replace("\\", "/"): text for path, text in sources.items()}
    known = set(normalized) | {path.replace("\\", "/") for path in (known_paths or ())}
    scenes = {path: text for path, text in normalized.items() if path.lower().endswith(SCENE_SUFFIX)}
    main = _main_scene(normalized.get("project.godot", ""))
    diagnostics: list[dict] = []
    if not main:
        diagnostics.append({"kind": "missing_main_scene", "reason": "project.godot has no application/run/main_scene"})
    elif main not in scenes:
        diagnostics.append({"kind": "missing_main_scene", "path": main, "reason": "configured main scene is not scanned"})

    parsed: dict[str, dict] = {}
    scene_edges: list[dict] = []
    for path, text in sorted(scenes.items()):
        scene, refs, issues = _parse_scene(path, text)
        parsed[path] = scene
        scene_edges.extend(refs)
        diagnostics.extend(issues)

    for scene in parsed.values():
        for key, target in list(scene.get("external_resources", {}).items()):
            scene["external_resources"][key] = _resolve_target(scene["path"], target, known)
        for node in scene.get("nodes", []):
            if node.get("instance"):
                node["instance"] = _resolve_target(scene["path"], node["instance"], known)
            node["resources"] = [_resolve_target(scene["path"], value, known) if not value.startswith("SubResource(") else value for value in node.get("resources", [])]
    for edge in scene_edges:
        edge["target"] = _resolve_target(edge["source"], edge["target"], known)

    code_references: list[dict] = []
    for path, text in normalized.items():
        if not path.lower().endswith((".gd", ".cs")):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            found_literal = False
            for match in _RES_PATH.finditer(line):
                found_literal = True
                target = _resolve_target(path, _clean(match.group(1)), known)
                suffix = PurePosixPath(target).suffix.lower()
                if suffix == SCENE_SUFFIX:
                    level, evidence = _scene_evidence(line)
                    code_references.append({"source": path, "target": target, "line": line_no, "kind": "scene-reference", "classification": "static-reference", "evidence_level": level, "evidence": evidence})
                elif suffix in CONFIG_SUFFIXES:
                    code_references.append({"source": path, "target": target, "line": line_no, "kind": "config-reference", "classification": "static-reference", "evidence_level": "possible"})
                elif suffix in ASSET_SUFFIXES and "{" not in target and "}" not in target:
                    code_references.append({"source": path, "target": target, "line": line_no, "kind": "asset-reference", "classification": "static-reference", "evidence_level": "possible"})
            if re.search(r"\b(?:load|preload|ResourceLoader\.load)\s*\(", line) and not found_literal:
                diagnostics.append({"kind": "dynamic-reference", "source": path, "line": line_no, "classification": "dynamic-unknown", "evidence": line.strip()[:400]})

    effective_pairs = {(item["source"], item["target"]) for item in code_references if item.get("kind") == "scene-reference" and item.get("evidence_level") == "effective"}
    code_references = [item for item in code_references if not (item.get("kind") == "scene-reference" and item.get("evidence_level") == "possible" and (item["source"], item["target"]) in effective_pairs)]

    for scene_path, scene in parsed.items():
        scripts = sorted({value for value in scene.get("external_resources", {}).values() if value.endswith((".gd", ".cs"))})
        events: set[str] = set()
        functions: set[str] = set()
        configs: set[str] = set()
        routes: set[str] = set()
        for script in scripts:
            text = normalized.get(script, "")
            events.update(re.findall(r'(?:Publish|PublishSimple)\s*\(\s*["\']([^"\']+)', text))
            events.update(re.findall(r'["\'](ui\.[A-Za-z0-9_.-]+)["\']', text))
            functions.update(re.findall(r"\b(?:func|void|bool|private|public|protected|internal|static)\s+([A-Za-z_]\w*)\s*\(", text))
            for ref in code_references:
                if ref.get("source") != script:
                    continue
                if ref.get("kind") == "config-reference":
                    configs.add(ref["target"])
                if ref.get("kind") == "scene-reference":
                    routes.add(ref["target"])
                    if ref.get("target") != scene_path:
                        scene_edges.append({**ref, "source": scene_path, "kind": "script-reference"})
        scene["functional_summary"] = {
            "scripts": scripts,
            "events": sorted(events),
            "functions": sorted(functions),
            "scene_routes": sorted(routes),
            "node_types": sorted({node.get("type", "") for node in scene.get("nodes", []) if node.get("type")}),
            "config_references": sorted(configs),
        }

    scene_edges = _dedupe_edges(scene_edges)
    adjacency: dict[str, list[dict]] = {}
    for edge in scene_edges:
        if edge.get("evidence_level", "possible") == "effective":
            adjacency.setdefault(str(edge.get("source")), []).append(edge)
    reachable: set[str] = set()
    queue: deque[str] = deque()
    if main in scenes:
        reachable.add(main)
        queue.append(main)
    while queue:
        source = queue.popleft()
        for edge in adjacency.get(source, []):
            target = str(edge.get("target"))
            if target in scenes and target not in reachable:
                reachable.add(target)
                queue.append(target)

    colors: dict[str, int] = {}
    def visit(source: str) -> None:
        colors[source] = 1
        for edge in adjacency.get(source, []):
            target = str(edge.get("target"))
            if target not in reachable:
                continue
            if colors.get(target) == 1:
                diagnostics.append({"kind": "cycle", "source": source, "target": target, "line": edge.get("line")})
            elif colors.get(target, 0) == 0:
                visit(target)
        colors[source] = 2
    if main in reachable:
        visit(main)

    nodes = {path: {**data, "classification": "confirmed-reachable" if path in reachable else "unreachable-candidate"} for path, data in parsed.items()}
    for detail in task_details or []:
        task = detail.get("task", {})
        for binding in detail.get("godot", {}).get("scenes", []):
            scene = nodes.get(binding.get("scene"))
            if scene is not None:
                scene.setdefault("knowledge_context", []).append({"task_id": task.get("id"), "title": task.get("title"), "status": task.get("status"), "level": "verified", "evidence": binding.get("kind"), "witness": binding.get("witness")})
        for candidate in detail.get("godot", {}).get("candidates", []):
            scene = nodes.get(candidate.get("scene"))
            if scene is not None:
                scene.setdefault("knowledge_context", []).append({"task_id": task.get("id"), "title": task.get("title"), "status": task.get("status"), "level": "candidate", "evidence": candidate.get("kind"), "source": candidate.get("evidence")})
    for scene in nodes.values():
        unique: dict[str, dict] = {}
        for item in scene.get("knowledge_context", []):
            key = str(item.get("task_id"))
            if key not in unique or item.get("level") == "verified":
                unique[key] = item
        if unique:
            scene["knowledge_context"] = sorted(unique.values(), key=lambda item: (item.get("level") != "verified", str(item.get("task_id"))))

    script_task_context: dict[str, list[dict]] = {}
    for scene_path, scene in nodes.items():
        for script in scene.get("functional_summary", {}).get("scripts", []):
            for link in scene.get("knowledge_context", []):
                script_task_context.setdefault(script, []).append({"task_id": link.get("task_id"), "title": link.get("title"), "level": link.get("level"), "relation": "scene-inherited", "scene": scene_path, "evidence": link.get("evidence")})

    return {
        "schema_version": "newrouge.godot-scene-graph.v1",
        "main_scene": main,
        "nodes": nodes,
        "edges": scene_edges,
        "code_references": sorted(code_references, key=lambda item: (str(item.get("source")), int(item.get("line") or 0), str(item.get("target")))),
        "script_task_context": script_task_context,
        "diagnostics": diagnostics,
    }
