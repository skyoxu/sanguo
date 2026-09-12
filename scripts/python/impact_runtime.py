"""Bounded parser for explicit Godot scene/resource runtime bindings."""
from __future__ import annotations
import re
import hashlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RuntimeBinding:
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    relation: str
    line: int

def _clean(value: str) -> str:
    return value.strip().strip('"')

def parse_runtime_bindings(path: str, text: str, hashes: dict[str, str], *, allowed_script_paths: set[str] | None = None) -> list[dict[str, str]]:
    """Parse explicit .tscn/.tres declarations without evaluating expressions."""
    if not isinstance(text, str) or path not in hashes:
        raise ValueError("source_read_failure")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != hashes[path]:
        raise ValueError("stale_index")
    if not path.lower().endswith((".tscn", ".tres")):
        return []
    lines = text.splitlines(); ext: dict[str, str] = {}; sub: dict[str, str] = {}
    out: list[dict[str, str]] = []; scene = path.replace('\\','/')
    node_paths: dict[str, str] = {".": "."}; current = "."
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith(';') or line.startswith('#'): continue
        m = re.match(r'\[ext_resource\s+([^]]+)\]', line)
        if m:
            attrs = dict(re.findall(r'(\w+)\s*=\s*("[^"]*"|[^\s]+)', m.group(1)))
            rid = _clean(attrs.get('id','')); resource = _clean(attrs.get('path',''))
            if rid and resource: ext[rid] = resource
            continue
        m = re.match(r'\[sub_resource\s+([^]]+)\]', line)
        if m:
            attrs = dict(re.findall(r'(\w+)\s*=\s*("[^"]*"|[^\s]+)', m.group(1)))
            rid = _clean(attrs.get('id',''))
            if rid: sub[rid] = f"{scene}::subresource:{rid}"
            continue
        m = re.match(r'\[node\s+([^]]+)\]', line)
        if m:
            attrs = dict(re.findall(r'(\w+)\s*=\s*("[^"]*"|[^\s]+)', m.group(1)))
            name = _clean(attrs.get('name','')); parent = _clean(attrs.get('parent','.')) or '.'
            current = name if parent == '.' else f"{parent}/{name}"
            node_paths[current] = current
            continue
        for key, value in re.findall(r'\b([A-Za-z_][\w/]*)\s*=\s*([^\s]+)', line):
            value = _clean(value)
            ref_match = re.fullmatch(r'(ExtResource|SubResource)\("([^"]+)"\)', value)
            ref = ref_match
            target = None
            if ref:
                ref_kind, ref_id = ref.group(1), ref.group(2)
                table = ext if ref_kind == "ExtResource" else sub
                if ref_id not in table:
                    raise ValueError("source_read_failure")
                value = table[ref_id]
                target = value
            else:
                target = ext.get(value) or sub.get(value)
            if not target: continue
            if target.startswith('res://'): target = target[6:]
            if key == 'script' and allowed_script_paths is not None and target not in allowed_script_paths: continue
            tk = 'script' if key == 'script' else 'resource'
            out.append({'from': f'{scene}::node:{current}', 'from_kind':'node', 'to':target, 'to_kind':tk, 'relation':'binds', 'evidence_path':scene, 'evidence_anchor':f'line:{n}-{n}', 'evidence_sha256':hashes[path]})
        m = re.match(r'\[connection\s+([^]]+)\]', line)
        if m:
            attrs = dict(re.findall(r'(\w+)\s*=\s*("[^"]*"|[^\s]+)', m.group(1)))
            signal = _clean(attrs.get('signal','')); from_node = _clean(attrs.get('from','.')); to_node = _clean(attrs.get('to','.'))
            if signal and from_node and to_node:
                sid = f'{scene}::signal:{from_node}:{signal}'
                out.append({'from':f'{scene}::node:{to_node}','from_kind':'node','to':sid,'to_kind':'signal','relation':'binds','evidence_path':scene,'evidence_anchor':f'line:{n}-{n}','evidence_sha256':hashes[path]})
    return out
