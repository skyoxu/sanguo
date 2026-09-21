#!/usr/bin/env python3
"""Capture task resource knowledge as an explicit Chapter 6 stage."""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

GODOT_PATH_SUFFIXES = ('.tscn', '.gd', '.cs', '.tres', '.res', '.json', '.csv', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.wav', '.ogg', '.mp3')

def _changed_paths(root: Path) -> set[str]:
    try:
        proc = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], cwd=root, text=True,
                              encoding='utf-8', capture_output=True, check=False)
        return {line.replace('\\', '/') for line in proc.stdout.splitlines() if line.strip()}
    except OSError:
        return set()

def _capture_element_manifest(root: Path, task_id: str, out_dir: Path) -> dict:
    latest = root / 'logs/ci/project-health-knowledge/latest.json'
    state = json.loads(latest.read_text(encoding='utf-8')) if latest.exists() else {}
    graph = state.get('scene_graph') or {}
    links_path = root / 'docs/knowledge/generated/task-resource-links.json'
    links = json.loads(links_path.read_text(encoding='utf-8')) if links_path.exists() else {'generated': []}
    entries = [entry for entry in links.get('generated', []) if str(entry.get('task_id')) == str(task_id)]
    elements = []
    seen = set()
    for entry in entries:
        path = str(entry.get('path') or '').replace('\\', '/')
        if not path or path in seen:
            continue
        seen.add(path)
        item = {'path': path, 'kind': entry.get('kind'), 'status': 'verified' if entry.get('confidence') == 'confirmed' else 'inferred', 'evidence': entry.get('evidence', [])}
        if item['kind'] == 'scene' and path in graph.get('nodes', {}):
            scene = graph['nodes'][path]
            item['nodes'] = [{'path': f"{node.get('parent') or '.'}/{node.get('name') or '(unnamed)'}", 'type': node.get('type')} for node in scene.get('nodes', [])]
            item['scripts'] = scene.get('functional_summary', {}).get('scripts', [])
            item['events'] = scene.get('functional_summary', {}).get('events', [])
        if item['kind'] in {'config', 'asset'}:
            item['readers'] = entry.get('readers', [])
        elements.append(item)
    changed = _changed_paths(root)
    linked = {item['path'] for item in elements}
    for path in sorted(changed - linked):
        if path.lower().endswith(GODOT_PATH_SUFFIXES):
            kind = 'scene' if path.lower().endswith('.tscn') else 'script' if path.lower().endswith(('.gd', '.cs')) else 'resource'
            elements.append({'path': path, 'kind': kind, 'status': 'unmapped', 'evidence': [{'source': 'git-diff'}]})
    gaps = []
    for item in elements:
        if item['status'] == 'unmapped':
            gaps.append({'severity': 'P1' if item['kind'] in {'scene', 'script'} else 'P2', 'path': item['path'], 'reason': 'Changed Godot element has no task resource binding.'})
        elif item['kind'] in {'scene', 'asset', 'config'} and not any(e.get('focus') == 'core' for e in item.get('evidence', []) if isinstance(e, dict)):
            gaps.append({'severity': 'P2', 'path': item['path'], 'reason': 'Resource is recorded but lacks confirmed semantic focus.'})
    payload = {'schema_version': 'newrouge.chapter6-element-capture.v1', 'task_id': str(task_id), 'source_revision': state.get('revision'), 'elements': elements, 'documentation_gaps': gaps, 'blocking': False}
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / 'knowledge-capture-candidate.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    gaps_out = out_dir / 'documentation-gaps.md'
    lines = [f'# Chapter 6 documentation gaps: task {task_id}', '', 'Generated from deterministic scan. These gaps are non-blocking follow-up items.', '']
    if gaps:
        lines.extend(f"- [{gap['severity']}] `{gap['path']}`: {gap['reason']}" for gap in gaps)
    else:
        lines.append('- No documentation gaps detected.')
    gaps_out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'path': str(out.relative_to(root)).replace('\\', '/'), 'elements': len(elements), 'documentation_gaps': len(gaps), 'blocking': False, 'scope': 'task-local-staging'}

def _semantic_prompt_entries(entries: list[dict]) -> list[dict]:
    compact = []
    for entry in entries:
        kind = entry.get('kind')
        if kind not in {'config', 'asset', 'scene'}:
            continue
        item = {key: entry.get(key) for key in (
            'id', 'path', 'kind', 'role', 'task_title', 'readers', 'bindings', 'evidence', 'test_refs')}
        item.pop('bindings', None)
        if kind == 'config':
            fields = entry.get('parameters') if isinstance(entry.get('parameters'), list) else []
            prioritized = sorted(
                (field for field in fields if isinstance(field, dict) and isinstance(field.get('pointer'), str)),
                key=lambda field: (field.get('kind') != 'numeric_parameter', field.get('line') or 0),
            )
            item['available_parameters'] = [
                {key: field.get(key) for key in ('pointer', 'value', 'line', 'record_id', 'kind')}
                for field in prioritized[:80]
            ]
            item['available_parameters_truncated'] = len(fields) > 80
        elif kind == 'asset':
            bindings = entry.get('bindings') if isinstance(entry.get('bindings'), list) else []
            item['available_bindings'] = [
                {key: binding.get(key) for key in ('source', 'line', 'evidence')}
                for binding in bindings[:12] if isinstance(binding, dict)
            ]
            item['available_bindings_truncated'] = len(bindings) > 12
        else:
            bindings = entry.get('bindings') if isinstance(entry.get('bindings'), list) else []
            item['available_bindings'] = [{
                'node_path': binding.get('node_path'), 'type': binding.get('type'), 'line': binding.get('line'),
                'properties': [{key: prop.get(key) for key in ('name', 'value', 'line')}
                               for prop in binding.get('properties', [])[:12] if isinstance(prop, dict)],
            } for binding in bindings[:20] if isinstance(binding, dict)]
            item['available_bindings_truncated'] = len(bindings) > 20
        compact.append(item)
    return compact

def _validate_semantic_entries(model: object, entries: list[dict]) -> tuple[bool, list[dict], str | None]:
    if not isinstance(model, list) or not all(isinstance(item, dict) for item in model):
        return False, [], 'Semantic output must be an array of objects'
    available = {str(entry.get('path')): entry for entry in entries if entry.get('path')}
    normalized = []
    for item in model:
        path = str(item.get('path') or '')
        if path not in available:
            return False, [], f'Unknown resource path: {path}'
        parameters = item.get('parameters', [])
        if not isinstance(parameters, list) or not all(isinstance(parameter, dict) for parameter in parameters):
            return False, [], f'Parameters must be an array of objects: {path}'
        source = available[path]
        fields = source.get('parameters') if source.get('kind') == 'config' else []
        fields_by_pointer = {
            str(field.get('pointer')): field for field in fields or []
            if isinstance(field, dict) and isinstance(field.get('pointer'), str)}
        validated_parameters = []
        for parameter in parameters:
            pointer = parameter.get('pointer') or parameter.get('key')
            if not isinstance(pointer, str) or pointer not in fields_by_pointer:
                return False, [], f'Unknown parameter pointer for {path}: {pointer}'
            field = fields_by_pointer[pointer]
            validated_parameters.append({
                'pointer': pointer,
                'meaning': str(parameter.get('meaning') or parameter.get('description') or ''),
                'value': field.get('value'),
                'line': field.get('line'),
                'evidence_status': 'field_exists_semantic_inference',
            })
        clean = dict(item)
        clean['id'] = source.get('id')
        clean['path'] = path
        clean['kind'] = source.get('kind')
        clean['parameters'] = validated_parameters
        bindings = item.get('bindings', [])
        if not isinstance(bindings, list) or not all(isinstance(binding, dict) for binding in bindings):
            return False, [], f'Bindings must be an array of objects: {path}'
        source_bindings = source.get('bindings') if isinstance(source.get('bindings'), list) else []
        validated_bindings = []
        if source.get('kind') == 'asset':
            available_bindings = {(binding.get('source'), binding.get('line')): binding
                                  for binding in source_bindings if isinstance(binding, dict)}
            for binding in bindings:
                if not str(binding.get('meaning') or '').strip():
                    return False, [], f'Binding meaning is required for {path}'
                key = (binding.get('source'), binding.get('line'))
                if key not in available_bindings:
                    return False, [], f'Unknown asset binding for {path}: {key}'
                actual = available_bindings[key]
                validated_bindings.append({
                    'source': actual.get('source'), 'line': actual.get('line'), 'evidence': actual.get('evidence'),
                    'meaning': str(binding.get('meaning') or ''),
                    'evidence_status': 'static_binding_semantic_explanation'})
        elif source.get('kind') == 'scene':
            available_bindings = {(binding.get('node_path'), binding.get('line')): binding
                                  for binding in source_bindings if isinstance(binding, dict)}
            for binding in bindings:
                if not str(binding.get('meaning') or '').strip():
                    return False, [], f'Binding meaning is required for {path}'
                key = (binding.get('node_path'), binding.get('line'))
                if key not in available_bindings:
                    return False, [], f'Unknown scene binding for {path}: {key}'
                actual = available_bindings[key]
                validated_bindings.append({
                    'node_path': actual.get('node_path'), 'type': actual.get('type'), 'line': actual.get('line'),
                    'meaning': str(binding.get('meaning') or ''),
                    'evidence_status': 'static_binding_semantic_explanation'})
        elif bindings:
            return False, [], f'Bindings are not supported for {path}'
        clean['bindings'] = validated_bindings
        normalized.append(clean)
    returned_kinds = {item.get('kind') for item in normalized}
    for required_kind in ('asset', 'scene'):
        if any(entry.get('kind') == required_kind for entry in entries) and required_kind not in returned_kinds:
            return False, [], f'Missing semantic {required_kind} entry'
    return True, normalized, None

def _build_semantic_prompt(prompt_entries: list[dict]) -> str:
    return ('Return a JSON array only. Explain each supplied config, asset, or scene resource for a developer implementing this task. '
            'Write all explanation fields in English. '
            'For each item keep id and path, then add explanation, modification_guidance, modification_impact, parameters, and bindings. '
            'parameters must be an array of objects with pointer and meaning. Use only exact pointer values listed in '
            'available_parameters for that same config; otherwise use an empty array. bindings must use exact source/line '
            'pairs for assets or exact node_path/line pairs for scenes from available_bindings; configs use an empty array. '
            'Explain asset replacement constraints and scene/node editing impact without claiming runtime observation. '
            'Every returned binding must have a non-empty meaning. Return at least one relevant asset and one relevant scene '
            'when those kinds are supplied. Select only task-relevant fields and bindings. '
            'Do not invent paths, fields, nodes, runtime observations, or evidence. Omit unrelated resources.\n' +
            json.dumps(prompt_entries, ensure_ascii=False, separators=(',', ':')))

def _semantic_enrich(root: Path, task_id: str, backend: str, out_dir: Path) -> dict:
    sys.path.insert(0, str(root / 'scripts/sc'))
    from _llm_backend import run_llm_exec
    links = root / 'docs/knowledge/generated/task-resource-links.json'
    payload = json.loads(links.read_text(encoding='utf-8')) if links.exists() else {'generated': []}
    entries = [x for x in payload.get('generated', []) if str(x.get('task_id')) == str(task_id)]
    candidates = [entry for entry in entries if entry.get('kind') == 'config']
    candidates += [entry for entry in entries if entry.get('kind') == 'asset'][:12]
    scenes = [entry for entry in entries if entry.get('kind') == 'scene']
    scenes.sort(key=lambda entry: entry.get('evidence', [{}])[0].get('focus') != 'core')
    candidates += scenes[:8]
    prompt_entries = _semantic_prompt_entries(candidates)
    prompt = _build_semantic_prompt(prompt_entries)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / 'semantic-candidate.json'
    rc, trace, command = 1, '', []
    validation_error = None
    model = None
    for attempt in range(1, 6):
        rc, trace, command = run_llm_exec(backend=backend, root=root, prompt=prompt, output_last_message=out, timeout_sec=300)
        if rc == 0:
            try:
                candidate = json.loads(out.read_text(encoding='utf-8'))
                valid, model, validation_error = _validate_semantic_entries(candidate, entries)
                if valid:
                    break
            except (OSError, json.JSONDecodeError) as exc:
                validation_error = str(exc)
        if attempt < 5:
            time.sleep(1)
    if rc != 0 or model is None:
        error = validation_error or trace[-1000:] or 'Semantic output validation failed'
        out.write_text(json.dumps({'status': 'unverified', 'task_id': task_id, 'generated_by': 'llm-assisted-semantic-analysis', 'attempts': 5, 'error': error}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return {'status': 'unverified', 'rc': rc, 'attempts': 5}
    out.write_text(json.dumps({'status': 'verified', 'task_id': task_id, 'generated_by': 'llm-assisted-semantic-analysis', 'backend': backend, 'entries': model}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'status': 'verified', 'entries': len(model), 'attempts': attempt, 'command': command}

def run(root: Path, task_id: str, write_task_refs: bool = False, semantic: bool = False, llm_backend: str = 'codex-cli') -> dict:
    """Capture task-local candidates only; never refresh/publish global Knowledge."""
    if write_task_refs:
        return {
            'status': 'knowledge_capture_failed',
            'task_id': task_id,
            'reason': 'chapter6_global_task_ref_write_forbidden',
            'global_refresh': 'forbidden',
            'steps': [],
        }
    out_dir = root / 'logs/ci/chapter6-knowledge' / f'task-{task_id}'
    capture = _capture_element_manifest(root, task_id, out_dir)
    result = {
        'status': 'knowledge_captured',
        'task_id': task_id,
        'capture': capture,
        'steps': [],
        'global_refresh': 'not_performed',
        'publication': 'not_performed',
        'project_health_scan': 'not_performed',
        'kcp_pointer_mutation': 'forbidden',
    }
    if semantic:
        result['semantic_status'] = _semantic_enrich(root, task_id, llm_backend, out_dir)
    return result

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument('--repo-root', type=Path, default=Path.cwd()); parser.add_argument('--task-id', required=True); parser.add_argument('--write-task-refs', action='store_true', help='legacy flag; rejected because Chapter 6 cannot mutate global/task Knowledge refs'); parser.add_argument('--semantic', action='store_true'); parser.add_argument('--llm-backend', default='codex-cli')
    args = parser.parse_args(argv)
    result = run(args.repo_root.resolve(), args.task_id, args.write_task_refs, args.semantic, args.llm_backend)
    print(json.dumps(result, ensure_ascii=False)); return 0 if result['status'] == 'knowledge_captured' else 1
if __name__ == '__main__': raise SystemExit(main())
