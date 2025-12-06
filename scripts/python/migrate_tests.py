#!/usr/bin/env python3
"""
Migrate representative tests from .export_exclude to Tests.Godot/tests with minimal fixes.

Fixes applied:
 - extends -> "res://addons/gdUnit4/src/GdUnitTestSuite.gd"
 - await_idle_frame/process_frame -> get_tree().process_frame
 - inject /root singletons in before(): EventBus/DataStore/SqlDb
 - wrap add_child(x) -> add_child(auto_free(x))
 - remove demo gating (_demo_enabled) blocks
 - replace GDScript := from external calls (best-effort) with =
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/".export_exclude"/"tests"
DST = ROOT/"Tests.Godot"/"tests"

PLANS = [
    ("UI/InventoryPanel_Tests.gd", "UI/test_inventory_panel.gd"),
    ("UI/ScorePanel_Tests.gd", "UI/test_score_panel.gd"),
    ("UI/SettingsPanel_Tests.gd", "UI/test_settings_panel_logic.gd"),
]

def load(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def save(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def remove_demo_gating(code: str) -> str:
    lines = code.splitlines()
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.search(r"^\s*if\s+not\s+_demo_enabled\(\)\s*:\s*$", ln):
            # skip subsequent lines until an explicit 'return' (max 3 lines safeguard)
            j = i + 1
            k = 0
            while j < len(lines) and k < 4 and not re.search(r"^\s*return\s*$", lines[j]):
                j += 1; k += 1
            if j < len(lines) and re.search(r"^\s*return\s*$", lines[j]):
                i = j + 1
            else:
                i = j
            continue
        out.append(ln)
        i += 1
    return "\n".join(out) + "\n"

def inject_before(code: str) -> str:
    inject = []
    if '"/root/EventBus"' in code or 'get_node_or_null("/root/EventBus")' in code:
        inject += [
            '    var __bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()',
            '    __bus.name = "EventBus"',
            '    get_tree().get_root().add_child(auto_free(__bus))',
        ]
    if '"/root/DataStore"' in code or 'get_node_or_null("/root/DataStore")' in code:
        inject += [
            '    var __ds = preload("res://Game.Godot/Adapters/DataStoreAdapter.cs").new()',
            '    __ds.name = "DataStore"',
            '    get_tree().get_root().add_child(auto_free(__ds))',
        ]
    if '"/root/SqlDb"' in code or 'get_node_or_null("/root/SqlDb")' in code:
        inject += [
            '    var __db = preload("res://Game.Godot/Adapters/SqliteDataStore.cs").new()',
            '    __db.name = "SqlDb"',
            '    get_tree().get_root().add_child(auto_free(__db))',
        ]
    if not inject:
        return code
    if re.search(r'^func\s+before\(\)\s*->\s*void:\s*$', code, flags=re.M):
        return re.sub(r'^(func\s+before\(\)\s*->\s*void:\s*\n)', r"\1"+"\n".join(inject)+"\n", code, flags=re.M)
    return re.sub(r'^(extends .*?\n)', r"\1\nfunc before() -> void:\n"+"\n".join(inject)+"\n\n", code, flags=re.M)

def migrate_one(rel_src: str, rel_dst: str):
    sp = SRC/rel_src
    if not sp.exists():
        print('SKIP (missing):', sp)
        return
    code = load(sp)
    code = re.sub(r'^extends\s+GdUnitTestSuite', 'extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"', code, flags=re.M)
    code = code.replace('await await_idle_frame()', 'await get_tree().process_frame')
    code = code.replace('await await_idle_frame', 'await get_tree().process_frame')
    code = code.replace('await process_frame', 'await get_tree().process_frame')
    code = remove_demo_gating(code)
    code = inject_before(code)
    code = re.sub(r'add_child\(([^)\n]+)\)', r'add_child(auto_free(\1))', code)
    code = re.sub(r'var\s+(\w+)\s*:=\s*(_\w+\.[^\n]+)', r'var \1 = \2', code)
    dp = DST/rel_dst
    save(dp, code)
    print('MIGRATED ->', dp)

def main():
    print('SRC:', SRC)
    print('DST:', DST)
    for s, d in PLANS:
        migrate_one(s, d)

if __name__ == '__main__':
    main()

