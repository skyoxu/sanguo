import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/python'))
import chapter6_knowledge


class Chapter6KnowledgeTests(unittest.TestCase):
    def test_semantic_parameters_must_match_exact_config_pointer(self):
        entries = [{'id': 'config:192:data.json', 'path': 'data.json', 'kind': 'config',
                    'parameters': [{'pointer': '/menu/0/label', 'value': 'Start', 'line': 3}]}]
        valid, model, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'data.json', 'parameters': [{'pointer': '/menu/0/missing', 'meaning': 'Missing'}]}], entries)
        self.assertFalse(valid)
        self.assertFalse(model)
        self.assertIn('Unknown parameter pointer', error)

    def test_semantic_prompt_includes_configs_assets_and_scenes(self):
        prompt_entries = chapter6_knowledge._semantic_prompt_entries([
            {'path': 'image.png', 'kind': 'asset', 'bindings': [{'source': 'ui.gd', 'line': 7, 'evidence': 'load image'}]},
            {'path': 'scene.tscn', 'kind': 'scene', 'bindings': [{'node_path': 'VBox/Start', 'type': 'Button', 'line': 12, 'properties': []}]},
            {'path': 'data.json', 'kind': 'config', 'parameters': [{'pointer': '/cost', 'value': 2, 'line': 2, 'kind': 'numeric_parameter'}]},
        ])
        self.assertEqual([entry['path'] for entry in prompt_entries], ['image.png', 'scene.tscn', 'data.json'])
        self.assertEqual(prompt_entries[0]['available_bindings'][0]['source'], 'ui.gd')
        self.assertEqual(prompt_entries[1]['available_bindings'][0]['node_path'], 'VBox/Start')
        self.assertEqual(prompt_entries[2]['available_parameters'][0]['pointer'], '/cost')

    def test_failure_is_explicit_and_stops_at_failing_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chapter6_knowledge.run(Path(tmp), '192')
            self.assertEqual(result['status'], 'knowledge_capture_failed')
            self.assertEqual(result['stop_step'], 1)

    def test_capture_element_manifest_is_non_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'logs/ci/project-health-knowledge').mkdir(parents=True)
            (root / 'docs/knowledge/generated').mkdir(parents=True)
            (root / 'logs/ci/project-health-knowledge/latest.json').write_text(
                json.dumps({'revision': 'directory:test', 'tasks': [], 'sources': {}, 'file_manifest': []}), encoding='utf-8')
            (root / 'docs/knowledge/generated/task-resource-links.json').write_text(json.dumps({'generated': [
                {'task_id': '192', 'path': 'Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn',
                 'kind': 'scene', 'confidence': 'confirmed', 'evidence': []}]}), encoding='utf-8')
            result = chapter6_knowledge._capture_element_manifest(root, '192')
            payload = json.loads((root / result['path']).read_text(encoding='utf-8'))
            self.assertEqual(payload['elements'][0]['status'], 'verified')
            self.assertFalse(payload['blocking'])
            self.assertTrue((root / 'docs/knowledge/generated/chapter6-task-192-documentation-gaps.md').exists())


if __name__ == '__main__':
    unittest.main()
