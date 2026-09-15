from __future__ import annotations

import unittest

from scripts.python._godot_scene_graph import build_scene_graph


class GodotSceneGraphTests(unittest.TestCase):
    def test_explicit_scene_switch_is_effective_and_reachable(self) -> None:
        sources = {
            'project.godot': '[application]\nrun/main_scene="res://Game.Godot/Scenes/Main.tscn"\n',
            'Game.Godot/Scenes/Main.tscn': '[gd_scene load_steps=2 format=3]\n[ext_resource path="res://Game.Godot/Scripts/Main.gd" type="Script" id="1"]\n[node name="Main" type="Node"]\nscript = ExtResource("1")\n',
            'Game.Godot/Scenes/Battle.tscn': '[gd_scene format=3]\n[node name="Battle" type="Node"]\n',
            'Game.Godot/Scripts/Main.gd': 'func go():\n    get_tree().change_scene_to_file("res://Game.Godot/Scenes/Battle.tscn")\n',
        }
        graph = build_scene_graph(sources, known_paths=tuple(sources))
        self.assertEqual(graph['main_scene'], 'Game.Godot/Scenes/Main.tscn')
        self.assertEqual(graph['nodes']['Game.Godot/Scenes/Main.tscn']['classification'], 'confirmed-reachable')
        self.assertEqual(graph['nodes']['Game.Godot/Scenes/Battle.tscn']['classification'], 'confirmed-reachable')
        edges = [item for item in graph['edges'] if item.get('target') == 'Game.Godot/Scenes/Battle.tscn']
        self.assertTrue(any(item.get('evidence_level') == 'effective' for item in edges))

    def test_literal_only_scene_reference_remains_possible(self) -> None:
        sources = {
            'project.godot': '[application]\nrun/main_scene="res://Main.tscn"\n',
            'Main.tscn': '[gd_scene load_steps=2 format=3]\n[ext_resource path="res://Main.gd" type="Script" id="1"]\n[node name="Main" type="Node"]\nscript = ExtResource("1")\n',
            'Hidden.tscn': '[gd_scene format=3]\n[node name="Hidden" type="Node"]\n',
            'Main.gd': 'const HIDDEN = "res://Hidden.tscn"\n',
        }
        graph = build_scene_graph(sources, known_paths=tuple(sources))
        self.assertEqual(graph['nodes']['Hidden.tscn']['classification'], 'unreachable-candidate')
        refs = [item for item in graph['code_references'] if item.get('target') == 'Hidden.tscn']
        self.assertEqual(refs[0]['evidence_level'], 'possible')

    def test_scene_nodes_and_resource_references_are_preserved(self) -> None:
        sources = {
            'project.godot': '[application]\nrun/main_scene="res://UI.tscn"\n',
            'UI.tscn': '[gd_scene load_steps=3 format=3]\n[ext_resource path="res://ui.gd" type="Script" id="1"]\n[ext_resource path="res://icon.png" type="Texture2D" id="2"]\n[node name="UI" type="Control"]\nscript = ExtResource("1")\n[node name="Icon" type="TextureRect" parent="."]\ntexture = ExtResource("2")\n',
            'ui.gd': 'func _ready():\n    var cfg = load("res://settings.json")\n',
            'settings.json': '{}',
            'icon.png': '',
        }
        graph = build_scene_graph(sources, known_paths=tuple(sources))
        scene = graph['nodes']['UI.tscn']
        self.assertEqual(scene['functional_summary']['scripts'], ['ui.gd'])
        self.assertTrue(any(node.get('name') == 'Icon' for node in scene['nodes']))
        self.assertTrue(any(item.get('kind') == 'config-reference' and item.get('target') == 'settings.json' for item in graph['code_references']))

    def test_task_scene_binding_is_exposed_as_verified_context(self) -> None:
        sources = {
            'project.godot': '[application]\nrun/main_scene="res://Main.tscn"\n',
            'Main.tscn': '[gd_scene format=3]\n[node name="Main" type="Node"]\n',
        }
        tasks = [{'task': {'id': 192, 'title': 'Main menu', 'status': 'done'}, 'godot': {'scenes': [{'scene': 'Main.tscn', 'kind': 'configured', 'witness': 'main'}], 'candidates': []}}]
        graph = build_scene_graph(sources, tasks, tuple(sources))
        context = graph['nodes']['Main.tscn']['knowledge_context']
        self.assertEqual(context[0]['task_id'], 192)
        self.assertEqual(context[0]['level'], 'verified')


if __name__ == '__main__':
    unittest.main()
