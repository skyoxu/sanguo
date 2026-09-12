"""Task SSOT projections and conservative scene attachment evidence."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


def task_details(root) -> list[dict]:
    """Read the task triplet from a source adapter or a filesystem root."""
    def read(relative: str):
        if not isinstance(root, Path):
            return json.loads(root.read_text(relative))
        return json.loads((root / Path(relative)).read_text(encoding='utf-8-sig'))
    tasks = read('.taskmaster/tasks/tasks.json')['master']['tasks']
    views = {name: read(f'.taskmaster/tasks/{name}.json')
             for name in ('tasks_back', 'tasks_gameplay')}
    result = []
    seen = set()
    for task in tasks:
        identity = str(task['id'])
        if identity in seen:
            raise ValueError(f'Duplicate SSOT task id: {identity}')
        seen.add(identity)
        mappings = {name: [{key: value for key, value in row.items() if key not in task}
                           for row in rows if str(row.get('taskmaster_id')) == identity]
                    for name, rows in views.items()}
        result.append({'task': task, 'mappings': mappings})
    return result


def scene_bindings(sources: dict[str, str]) -> list[dict]:
    """Only script assignments on actual scene nodes count as attachments."""
    result = []
    for path, text in sorted(sources.items()):
        if not path.startswith('Game.Godot/') or not path.endswith('.tscn'):
            continue
        resources = {}
        node = None
        for number, line in enumerate(text.splitlines(), 1):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', line))
            if line.startswith('[ext_resource'):
                resources[attrs.get('id')] = attrs.get('path', '').removeprefix('res://')
            elif line.startswith('[node '):
                name, parent = attrs.get('name', ''), attrs.get('parent')
                node = '.' if parent is None else (name if parent == '.' else f'{parent}/{name}')
            elif line.startswith('['):
                node = None
            match = re.fullmatch(r'\s*script\s*=\s*ExtResource\("([^"]+)"\)\s*', line)
            if match and node is not None:
                script = resources.get(match[1])
                if script in sources:
                    result.append({'scene': path, 'node': node, 'script': script, 'line': number})
    return result


def attach_task_scenes(details: list[dict], sources: dict[str, str], declarations: list[dict]) -> None:
    bindings = scene_bindings(sources)
    for detail in details:
        task_id = str(detail['task']['id'])
        # Task references and test scene loads are candidates, never implementation proof.
        combined = json.dumps(detail, ensure_ascii=False)
        tests = [path for path in sources if path.startswith(('Tests.Godot/', 'Game.Core.Tests/'))
                 and path in combined]
        candidates = []
        for test in tests:
            for scene in sorted(set(re.findall(r'res://([^"\s]+\.tscn)', sources[test]))):
                if scene in sources and scene.startswith('Game.Godot/'):
                    candidates.append({'scene': scene, 'evidence': test, 'kind': 'test_reference'})
        confirmed, invalid = [], []
        for declaration in declarations:
            if str(declaration.get('task_id')) != task_id:
                continue
            matches = [binding for binding in bindings
                       if all(binding[key] == declaration.get(key) for key in ('scene', 'node', 'script'))]
            # The configured witness must exist in the attached production script.
            witness = declaration.get('witness', '')
            if matches and isinstance(witness, str) and witness.strip() and witness in sources[matches[0]['script']]:
                confirmed.append({**matches[0], 'witness': witness,
                                  'kind': 'declared_task_with_verified_static_attachment'})
            else:
                invalid.append(declaration)
        detail['godot'] = {
            'status': 'static_attached' if confirmed else ('candidate' if candidates else 'unmapped'),
            'runtime_verified': False, 'scenes': confirmed, 'candidates': candidates,
            'invalid_declarations': invalid,
            'limitation': 'Static attachment is not runtime execution or acceptance proof. Unmapped does not mean absent.',
        }


def task_summary(details: list[dict]) -> dict:
    return {'total': len(details),
            'statuses': dict(Counter(str(item['task'].get('status', 'unknown')) for item in details)),
            'godot': dict(Counter(item['godot']['status'] for item in details))}


def task_page(details: list[dict], page: int, filter_kind: str | None = None,
              filter_value: str | None = None) -> dict:
    if filter_kind is not None:
        if filter_kind not in ('task_status', 'godot_status') or not filter_value:
            raise ValueError('Invalid task filter')
        if filter_kind == 'task_status':
            details = [item for item in details if str(item['task'].get('status', 'unknown')) == filter_value]
        else:
            details = [item for item in details if str(item['godot'].get('status', 'unmapped')) == filter_value]
    pages = max(1, (len(details) + 19) // 20)
    if page < 1 or page > pages:
        raise ValueError(f'Page must be between 1 and {pages}')
    keys = ('id', 'title', 'status', 'dependencies', 'recommendedSubtasks')
    return {'page': page, 'pages': pages, 'page_size': 20, 'total': len(details),
            'filter': {'kind': filter_kind, 'value': filter_value} if filter_kind else None,
            'items': [{**{key: row['task'].get(key) for key in keys}, 'godot': row['godot']}
                      for row in details[(page - 1) * 20:page * 20]]}
