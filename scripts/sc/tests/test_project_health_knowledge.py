"""Focused Project Health knowledge lifecycle regressions."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/python'))

from project_health_knowledge import (
    base_dir,
    build_godot_element_index,
    prune_query_evidence,
    write_json,
)


class ProjectHealthKnowledgeTests(unittest.TestCase):
    def test_godot_element_index_tracks_unmapped_and_stale_without_blocking(self):
        graph = {
            'nodes': {
                'Game.Godot/Scenes/Main.tscn': {
                    'classification': 'confirmed-reachable',
                    'nodes': [],
                    'functional_summary': {},
                }
            },
            'code_references': [],
        }
        result = build_godot_element_index(
            Path('.'),
            graph,
            {'Game.Godot/Scripts/Main.gd': 'extends Node', 'Game.Core/Service.cs': 'class Service {}'},
            [],
            {'elements': [{'path': 'Game.Godot/Scenes/Old.tscn'}]},
        )
        by_path = {item['path']: item for item in result['elements']}
        self.assertEqual(by_path['Game.Godot/Scenes/Main.tscn']['status'], 'verified')
        self.assertEqual(by_path['Game.Godot/Scripts/Main.gd']['status'], 'unmapped')
        self.assertNotIn('Game.Core/Service.cs', by_path)
        self.assertEqual(result['stale'][0]['path'], 'Game.Godot/Scenes/Old.tscn')
        self.assertFalse(result['blocking'])

    def test_prune_query_evidence_keeps_newest_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = base_dir(root) / 'queries'
            directory.mkdir(parents=True)
            for index in range(4):
                path = directory / f'{index}.json'
                write_json(path, {'index': index})
                stamp = 1_700_000_000 + index
                os.utime(path, (stamp, stamp))
            prune_query_evidence(root, keep=2)
            remaining = sorted(path.name for path in directory.glob('*.json'))
            self.assertEqual(remaining, ['2.json', '3.json'])


if __name__ == '__main__':
    unittest.main()
