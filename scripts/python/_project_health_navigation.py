"""Static, provenance-preserving task modification navigation."""
from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

CONFIG_SUFFIXES = {'.json', '.tres', '.cfg', '.ini', '.csv', '.yaml', '.yml'}
ASSET_SUFFIXES = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.ogg', '.wav', '.mp3', '.ttf', '.otf', '.glb'}
PATH_PATTERN = re.compile(r'(?:res://(?:\.\./)?|(?<![\w/]))((?:Game\.Core|Game\.Godot|Tests\.Godot|Game\.Core\.Tests)/[\w./-]+)')
QUOTED_PATH_PATTERN = re.compile(r'''(["'])(?:res://(?:\.\./)?)?((?:Game\.Core|Game\.Godot|Tests\.Godot|Game\.Core\.Tests)/[^"'\r\n]+)\1''')


def valid_path(path):
    return '..' not in PurePosixPath(path).parts and not any(c in path for c in ':\\')


def references(text, available=None):
    result = []
    for number, line in enumerate(text.splitlines(), 1):
        normalized = line.replace('\\\\', '/').replace('\\"', '"')
        quoted = list(QUOTED_PATH_PATTERN.finditer(normalized))
        matches = [(m.start(), m.group(2)) for m in quoted]
        matches.extend((m.start(), m.group(1).rstrip('.,;')) for m in PATH_PATTERN.finditer(normalized)
                       if not any(q.start() <= m.start() < q.end() for q in quoted))
        for _, path in sorted(matches):
            if available is None or (valid_path(path) and path in available):
                result.append({'path': path, 'line': number, 'evidence': line.strip()[:400], 'valid': valid_path(path)})
    return result


def fields(value, pointer='', identity=None):
    """Return exact JSON pointers and values, never inferred tuning constraints."""
    if isinstance(value, dict):
        identity = value.get('id', value.get('card_id', identity))
        for key, item in value.items():
            yield from fields(item, pointer + '/' + key.replace('~', '~0').replace('/', '~1'), identity)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from fields(item, pointer + '/' + str(index), identity)
    else:
        yield {'pointer': pointer, 'value': value, 'record_id': identity,
               'kind': 'numeric_parameter' if isinstance(value, (int, float)) and not isinstance(value, bool) else 'data_field'}


def scene_nodes(path, sources, available, visited=(), budget=None):
    """Resolve node property -> subresources -> external resources, with cycles bounded."""
    if budget is None:
        budget = [512]
    blocks, current = {}, None
    for number, line in enumerate(sources.get(path, '').splitlines(), 1):
        if re.match(r'^\[(?:gd_scene|gd_resource|ext_resource|sub_resource|node|resource|connection)(?:\s|\])', line):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', line))
            instance = re.search(r'instance=(ExtResource\("[^"]+"\))', line)
            if instance:
                attrs['instance'] = instance.group(1)
            kind = line[1:].split(' ', 1)[0].rstrip(']')
            key = (kind, attrs.get('id', str(number)))
            current = {'kind': kind, 'attrs': attrs, 'line': number, 'properties': []}
            blocks[key] = current
        elif current and re.match(r'^[\w/]+\s*=', line):
            key, value = line.split('=', 1)
            current['properties'].append({'name': key.strip(), 'value': value.strip(), 'line': number})
        elif current and current['properties'] and line.strip():
            current['properties'][-1]['value'] += '\n' + line.strip()

    def resolve(value, seen=()):
        results = []
        for kind, identity in re.findall(r'(ExtResource|SubResource)\("([^"]+)"\)', value):
            key = ('ext_resource' if kind == 'ExtResource' else 'sub_resource', identity)
            reference = kind + '(' + identity + ')'
            reason = ('expansion_limit' if budget[0] <= 0 else 'depth_limit' if len(seen) >= 32
                      else 'resource_cycle' if key in seen else 'resource_id_missing' if key not in blocks else None)
            budget[0] -= 1
            if reason:
                results.append({'path': '', 'available': False, 'chain': [reference], 'unresolved_reason': reason})
                if reason == 'expansion_limit':
                    break
                continue
            block = blocks[key]
            if kind == 'ExtResource':
                target = block['attrs'].get('path', '').removeprefix('res://')
                results.append({'path': target, 'available': valid_path(target) and target in available,
                                'chain': [kind + '(' + identity + ')'], 'line': block['line']})
                if not valid_path(target) or target not in available:
                    results[-1]['unresolved_reason'] = 'invalid_or_unscanned_path'
                elif PurePosixPath(target).suffix.lower() == '.tres':
                    reason = ('resource_cycle' if target in (*visited, path) else 'cross_resource_depth_limit' if len(visited) >= 8
                              else 'source_text_unavailable' if target not in sources else None)
                    if reason:
                        results[-1]['unresolved_reason'] = reason
                        continue
                    for node in scene_nodes(target, sources, available, (*visited, path), budget):
                        for prop in node['properties']:
                            for item in prop['resources']:
                                results.append({**item, 'chain': [kind + '(' + identity + ')', target, prop['name'], *item['chain']]})
            else:
                for prop in block['properties']:
                    for item in resolve(prop['value'], (*seen, key)):
                        results.append({**item, 'chain': [kind + '(' + identity + ')', prop['name'], *item['chain']]})
        return results

    result = []
    for block in blocks.values():
        if block['kind'] not in ('node', 'resource'):
            continue
        attrs = block['attrs']
        parent = attrs.get('parent')
        node_path = '.' if parent is None else '/'.join(x for x in (parent, attrs.get('name', '')) if x != '.')
        props = [{**prop, 'resources': resolve(prop['value'])} for prop in block['properties']]
        result.append({'scene': path, 'node_path': node_path, 'type': attrs.get('type', 'inherited'),
                       'line': block['line'], 'properties': props,
                       'instance': resolve(attrs.get('instance', ''))})
    return result


def located_fields(text):
    """Locate JSON leaves with the decoder, including repeated keys and compact JSON."""
    decoder = json.JSONDecoder()
    values = list(fields(json.loads(text)))
    positions = {}

    def walk(offset, pointer=''):
        while text[offset].isspace():
            offset += 1
        start = offset
        if text[offset] == '{':
            offset += 1
            while True:
                while text[offset].isspace() or text[offset] == ',':
                    offset += 1
                if text[offset] == '}':
                    return offset + 1
                key, offset = decoder.raw_decode(text, offset)
                while text[offset].isspace() or text[offset] == ':':
                    offset += 1
                offset = walk(offset, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
        if text[offset] == '[':
            offset += 1
            index = 0
            while True:
                while text[offset].isspace() or text[offset] == ',':
                    offset += 1
                if text[offset] == ']':
                    return offset + 1
                offset = walk(offset, pointer + '/' + str(index))
                index += 1
        _, end = decoder.raw_decode(text, offset)
        positions[pointer] = {'line': text.count('\n', 0, start) + 1,
                              'column': start - text.rfind('\n', 0, start), 'evidence': text[start:end]}
        return end

    walk(0)
    return [{**item, **positions[item['pointer']]} for item in values]


def focus_navigation(detail, sources, available):
    """Keep test fixtures and inferred identities out of the primary surface."""
    declared = references(json.dumps({'task': detail['task'], 'mappings': detail.get('mappings', {})}), available)
    core = {r['path'] for r in declared if r['path'].startswith(('Game.Core/', 'Game.Godot/'))}
    core.update(s['scene'] for s in detail.get('godot', {}).get('scenes', []) if s['scene'] in sources)
    for path in sorted(core.copy()):
        if PurePosixPath(path).suffix.lower() == '.tscn':
            for node in scene_nodes(path, sources, available):
                for prop in node['properties']:
                    if prop['name'] == 'script':
                        core.update(r['path'] for r in prop['resources'] if r.get('available'))
    primary = set(core)
    for path in sorted(primary):
        for ref in references(sources.get(path, ''), available):
            if PurePosixPath(ref['path']).suffix.lower() in CONFIG_SUFFIXES | ASSET_SUFFIXES:
                core.add(ref['path'])
        if path.lower().endswith('.tscn'):
            for node in scene_nodes(path, sources, available):
                for prop in node['properties']:
                    core.update(r['path'] for r in prop['resources'] if r.get('available') and
                                PurePosixPath(r['path']).suffix.lower() in CONFIG_SUFFIXES | ASSET_SUFFIXES)
    identity_text = json.dumps(detail['task']) + '\n' + '\n'.join(sources.get(p, '') for p in sorted(primary))
    identities = set(re.findall(r'\b(?:card|reward|deck|relic)\.[a-z0-9_.]+', identity_text))
    return core, identities


def build_navigation(detail, state):
    sources = state.get('sources', {})
    available = set(state.get('file_manifest', sources))
    core, focus_ids = focus_navigation(detail, sources, available)
    edges = {path: references(text, available) for path, text in sources.items()}
    task_text = json.dumps({'task': detail['task'], 'mappings': detail.get('mappings', {})}, ensure_ascii=False)
    declared = references(task_text)
    roots = {item['path'] for item in declared if item['valid'] and item['path'] in available}
    roots.update(item['scene'] for item in detail.get('godot', {}).get('scenes', []) if item['scene'] in sources)
    tests = sorted(path for path in roots if path.startswith(('Game.Core.Tests/', 'Tests.Godot/')))
    reached = {path: [{'path': path, 'kind': 'task_reference'}] for path in roots}
    # Symbol-name matches provide candidates, not a resolved call graph.
    test_text = '\n'.join(sources.get(path, '') for path in tests)
    for path in sources:
        if path.startswith(('Game.Core/', 'Game.Godot/')) and PurePosixPath(path).suffix.lower() == '.cs':
            name = PurePosixPath(path).stem
            if re.search(r'\b' + re.escape(name) + r'\b', test_text):
                reached.setdefault(path, [{'path': path, 'kind': 'test_symbol_candidate'}])
    for _ in range(5):
        additions = {}
        for path, chain in reached.items():
            for edge in edges.get(path, []):
                if edge['path'] not in reached:
                    additions.setdefault(edge['path'], [*chain, {'path': edge['path'], 'from': path,
                                                               'line': edge['line'], 'kind': 'literal_reference'}])
        if not additions:
            break
        reached.update(additions)
    card_ids = set(re.findall(r'card\.[a-z0-9_.]+', task_text + '\n' + test_text + '\n' + '\n'.join(
        sources.get(path, '') for path in reached if PurePosixPath(path).suffix.lower() == '.cs')))
    for path, text in sources.items():
        if path.startswith(('Game.Core/', 'Game.Godot/')) and PurePosixPath(path).suffix.lower() in CONFIG_SUFFIXES:
            overlap = sorted(card_ids & set(re.findall(r'card\.[a-z0-9_.]+', text)))
            if overlap:
                reached.setdefault(path, [{'path': path, 'kind': 'shared_card_id_candidate', 'matched_ids': overlap}])
    candidate_origins = {path: set(re.findall(r'card\.[a-z0-9_.]+', sources.get(path, '')))
                         for path in reached if PurePosixPath(path).suffix.lower() in CONFIG_SUFFIXES}
    for path, text in sources.items():
        if path in reached or not path.startswith(('Game.Core/', 'Game.Godot/')) or PurePosixPath(path).suffix.lower() not in CONFIG_SUFFIXES:
            continue
        identities = set(re.findall(r'card\.[a-z0-9_.]+', text))
        for origin, origin_ids in candidate_origins.items():
            overlap = sorted(identities & origin_ids)
            if overlap:
                reached[path] = [*reached[origin], {'path': path, 'from': origin,
                    'kind': 'shared_card_id_candidate', 'matched_ids': overlap}]
                break
    for _ in range(5):
        additions = {}
        for path, chain in reached.items():
            for edge in edges.get(path, []):
                if edge['path'] not in reached:
                    additions.setdefault(edge['path'], [*chain, {'path': edge['path'], 'from': path,
                        'line': edge['line'], 'kind': 'literal_reference'}])
        if not additions:
            break
        reached.update(additions)
    configs, code, scenes, assets = [], [], [], []
    for path, chain in sorted(reached.items()):
        suffix = PurePosixPath(path).suffix.lower()
        provenance = {'path': path, 'chain': chain, 'focus': 'core' if path in core else 'related', 'evidence_kind': 'static_candidate' if any(
            'candidate' in step['kind'] for step in chain) else 'static_reference', 'runtime_observed': False}
        if suffix in CONFIG_SUFFIXES and path.startswith(('Game.Core/', 'Game.Godot/')):
            # Keep source and target distinct in the reverse-reference index.
            readers = [{'reader': reader, 'line': edge['line'], 'evidence': edge['evidence']}
                       for reader, refs in edges.items() for edge in refs if edge['path'] == path]
            values, error = [], None
            if suffix == '.json':
                try:
                    values = located_fields(sources[path])
                except (ValueError, KeyError, RecursionError) as exc:
                    error = str(exc)
            configs.append({**provenance, 'fields': values[:500], 'field_count': len(values),
                            'focused_fields': [v for v in values if v.get('record_id') in focus_ids][:50],
                            'truncated': len(values) > 500, 'parse_error': error, 'readers': readers,
                            'activation': 'Literal references do not prove loading. Inspect the source; reload behavior is unknown.'})
        elif suffix in ('.cs', '.gd') and path.startswith(('Game.Core/', 'Game.Godot/')):
            code.append(provenance)
        elif suffix == '.tscn' and path.startswith('Game.Godot/'):
            scenes.append({**provenance, 'nodes': scene_nodes(path, sources, available)})
        elif suffix in ASSET_SUFFIXES:
            assets.append({**provenance, 'available': path in available,
                           'users': [{'source': reader, 'line': edge['line'], 'evidence': edge['evidence']}
                                     for reader, refs in edges.items() for edge in refs if edge['path'] == path]})
    return {'revision': state.get('revision'), 'configs': configs, 'code': code, 'scenes': scenes,
            'text_sources': sorted(sources),
            'unresolved_references': [{'source': path, **edge, 'reason': 'Not present in the scanned manifest' if edge['valid'] else 'Invalid repository path'}
                for path, refs in [('task declaration', declared), *((path, references(sources.get(path, ''))) for path in reached)]
                for edge in refs if not edge['valid'] or edge['path'] not in available],
            'assets': assets, 'tests': [{'path': path, 'evidence_kind': 'declared_test',
                'command_status': 'suggested_not_executed',
                'command': ('py -3 scripts/python/run_gdunit.py --godot-bin "$env:GODOT_BIN" --project Tests.Godot --prewarm --add "' + path.removeprefix('Tests.Godot/') + '"')
                if path.startswith('Tests.Godot/') else
                ('dotnet test Game.Core.Tests/Game.Core.Tests.csproj --filter "FullyQualifiedName~' + PurePosixPath(path).stem + '"')}
                for path in tests],
            'limitations': ['Static navigation does not prove runtime resource use.',
                'Symbol and shared-card-id links are candidates requiring inspection.',
                'Dynamic resource paths, runtime-created nodes and inherited overrides may be unresolved.',
                'Reference traversal stops after five hops; shared readers may belong to other tasks.',
                'Suggested test filters use file names: verify actual test types and matched counts; zero tests is not a passing verification.',
                'Directory snapshots omit files over 4 MiB, including large assets; Git asset manifests have no size limit.',
                'Resource expansion is bounded to 512 references, 32 subresource levels and eight cross-resource levels; unresolved reasons are displayed.',
                'Changing data does not change hard-coded service definitions or test expectations.']}
