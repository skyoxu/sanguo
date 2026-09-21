import tempfile
import unittest
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/python'))
import chapter6_knowledge

class Chapter6KnowledgeTests(unittest.TestCase):
    def test_semantic_parameters_must_match_exact_config_pointer(self):
        entries = [{'id': 'config:18:data.json', 'path': 'data.json', 'kind': 'config',
                    'parameters': [{'pointer': '/cards/0/cost', 'value': 1, 'line': 3}]}]
        valid, model, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'data.json', 'parameters': [{'pointer': '/cards/0/damage', 'meaning': 'Damage'}]}], entries)
        self.assertFalse(valid)
        self.assertFalse(model)
        self.assertIn('Unknown parameter pointer', error)

    def test_semantic_parameters_preserve_verified_field_location(self):
        entries = [{'id': 'config:18:data.json', 'path': 'data.json', 'kind': 'config',
                    'parameters': [{'pointer': '/cards/0/cost', 'value': 1, 'line': 3}]}]
        valid, model, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'data.json', 'explanation': 'Card data',
              'parameters': [{'key': '/cards/0/cost', 'meaning': 'Energy cost'}]}], entries)
        self.assertTrue(valid, error)
        self.assertEqual(model[0]['parameters'][0], {
            'pointer': '/cards/0/cost', 'meaning': 'Energy cost', 'value': 1, 'line': 3,
            'evidence_status': 'field_exists_semantic_inference'})
        self.assertEqual(model[0]['kind'], 'config')

    def test_semantic_output_rejects_non_object_entries(self):
        valid, _, error = chapter6_knowledge._validate_semantic_entries(['bad'], [])
        self.assertFalse(valid)
        self.assertIn('array of objects', error)

    def test_semantic_prompt_includes_configs_assets_and_scenes(self):
        prompt_entries = chapter6_knowledge._semantic_prompt_entries([
            {'path': 'image.png', 'kind': 'asset', 'bindings': [
                {'source': 'ui.gd', 'line': 7, 'evidence': 'load image'}]},
            {'path': 'scene.tscn', 'kind': 'scene', 'bindings': [
                {'node_path': 'Reward/Card', 'type': 'TextureRect', 'line': 12,
                 'properties': [{'name': 'texture', 'value': 'ExtResource("1")', 'line': 13}]}]},
            {'path': 'data.json', 'kind': 'config', 'parameters': [
                {'pointer': '/name', 'value': 'A', 'line': 1, 'kind': 'data_field'},
                {'pointer': '/cost', 'value': 2, 'line': 2, 'kind': 'numeric_parameter'},
            ]},
        ])
        self.assertEqual([entry['path'] for entry in prompt_entries], ['image.png', 'scene.tscn', 'data.json'])
        self.assertEqual(prompt_entries[0]['available_bindings'][0]['source'], 'ui.gd')
        self.assertEqual(prompt_entries[1]['available_bindings'][0]['node_path'], 'Reward/Card')
        self.assertEqual(prompt_entries[2]['available_parameters'][0]['pointer'], '/cost')

    def test_semantic_prompt_requires_english_explanations(self):
        prompt = chapter6_knowledge._build_semantic_prompt([])
        self.assertIn('Write all explanation fields in English', prompt)

    def test_semantic_asset_binding_must_match_source_and_line(self):
        entries = [{'id': 'asset:115:image.png', 'path': 'image.png', 'kind': 'asset',
                    'bindings': [{'source': 'ui.gd', 'line': 7, 'evidence': 'load image'}]}]
        valid, _, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'image.png', 'parameters': [], 'bindings': [
                {'source': 'ui.gd', 'line': 8, 'meaning': 'Card art'}]}], entries)
        self.assertFalse(valid)
        self.assertIn('Unknown asset binding', error)

    def test_semantic_binding_requires_explanation(self):
        entries = [{'id': 'asset:115:image.png', 'path': 'image.png', 'kind': 'asset',
                    'bindings': [{'source': 'ui.gd', 'line': 7, 'evidence': 'load image'}]}]
        valid, _, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'image.png', 'parameters': [], 'bindings': [
                {'source': 'ui.gd', 'line': 7, 'meaning': ''}]}], entries)
        self.assertFalse(valid)
        self.assertIn('Binding meaning is required', error)

    def test_semantic_output_requires_asset_and_scene_when_candidates_exist(self):
        entries = [
            {'id': 'asset:115:image.png', 'path': 'image.png', 'kind': 'asset',
             'bindings': [{'source': 'ui.gd', 'line': 7, 'evidence': 'load image'}]},
            {'id': 'scene:115:scene.tscn', 'path': 'scene.tscn', 'kind': 'scene',
             'bindings': [{'node_path': '.', 'line': 1, 'type': 'Control'}]},
        ]
        valid, _, error = chapter6_knowledge._validate_semantic_entries([], entries)
        self.assertFalse(valid)
        self.assertIn('Missing semantic asset entry', error)

    def test_semantic_scene_binding_preserves_verified_node_location(self):
        entries = [{'id': 'scene:115:reward.tscn', 'path': 'reward.tscn', 'kind': 'scene',
                    'bindings': [{'node_path': 'VBox/Card', 'type': 'TextureRect', 'line': 14,
                                  'properties': []}]}]
        valid, model, error = chapter6_knowledge._validate_semantic_entries(
            [{'path': 'reward.tscn', 'parameters': [], 'bindings': [
                {'node_path': 'VBox/Card', 'line': 14, 'meaning': 'Displays reward art'}]}], entries)
        self.assertTrue(valid, error)
        self.assertEqual(model[0]['bindings'][0]['type'], 'TextureRect')
        self.assertEqual(model[0]['bindings'][0]['evidence_status'], 'static_binding_semantic_explanation')

    def test_capture_is_task_local_even_when_global_scans_are_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = chapter6_knowledge.run(root, '18')
            self.assertEqual(result['status'], 'knowledge_captured')
            self.assertEqual(result['global_refresh'], 'not_performed')
            self.assertTrue((root / 'logs/ci/chapter6-knowledge/task-18/knowledge-capture-candidate.json').is_file())

    def test_legacy_write_task_refs_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = chapter6_knowledge.run(root, '18', write_task_refs=True)
            self.assertEqual(result['status'], 'knowledge_capture_failed')
            self.assertEqual(result['reason'], 'chapter6_global_task_ref_write_forbidden')

    def test_capture_element_manifest_records_inferred_and_unmapped_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'logs/ci/project-health-knowledge').mkdir(parents=True)
            (root / 'docs/knowledge/generated').mkdir(parents=True)
            (root / 'logs/ci/project-health-knowledge/latest.json').write_text(json.dumps({'revision': 'r1', 'scene_graph': {}}), encoding='utf-8')
            (root / 'docs/knowledge/generated/task-resource-links.json').write_text(json.dumps({'generated': [
                {'task_id': '7', 'path': 'Game.Godot/Scenes/Main.tscn', 'kind': 'scene', 'confidence': 'confirmed', 'evidence': []}]}), encoding='utf-8')
            out_dir = root / 'logs/ci/chapter6-knowledge/task-7'
            result = chapter6_knowledge._capture_element_manifest(root, '7', out_dir)
            payload = json.loads((root / result['path']).read_text(encoding='utf-8'))
            self.assertEqual(payload['elements'][0]['status'], 'verified')
            self.assertFalse(payload['blocking'])

if __name__ == '__main__':
    unittest.main()
