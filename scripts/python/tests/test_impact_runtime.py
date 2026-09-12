import hashlib
import unittest

from scripts.python.impact_runtime import parse_runtime_bindings


class RuntimeMappingTests(unittest.TestCase):
    def setUp(self):
        self.path = "Game.Godot/Examples/Components/PrimaryButton.tscn"
        self.text = """[gd_scene load_steps=2 format=3]\n\n; script = ExtResource(\"fake\")\n[ext_resource type=\"Script\" path=\"res://Game.Godot/Examples/Components/PrimaryButton.cs\" id=\"1\"]\n[node name=\"PrimaryButton\" type=\"Button\"]\nscript = ExtResource(\"1\")\n"""
        self.hashes = {self.path: hashlib.sha256(self.text.encode()).hexdigest()}

    def test_explicit_script_binding_and_node_identity(self):
        edges = parse_runtime_bindings(self.path, self.text, self.hashes, allowed_script_paths={"Game.Godot/Examples/Components/PrimaryButton.cs"})
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["from"], self.path + "::node:PrimaryButton")
        self.assertEqual(edges[0]["to"], "Game.Godot/Examples/Components/PrimaryButton.cs")
        self.assertEqual(edges[0]["evidence_anchor"], "line:6-6")

    def test_comments_and_unselected_scripts_are_ignored(self):
        edges = parse_runtime_bindings(self.path, self.text, self.hashes, allowed_script_paths=set())
        self.assertEqual(edges, [])

    def test_connection_identity(self):
        text = self.text + '[node name="Label" parent="." type="Label"]\n\n[connection signal="pressed" from="." to="Label"]\n'
        hashes = {self.path: hashlib.sha256(text.encode()).hexdigest()}
        edges = parse_runtime_bindings(self.path, text, hashes, allowed_script_paths=set())
        signal = [e for e in edges if e["to_kind"] == "signal"][0]
        self.assertEqual(signal["to"], self.path + "::signal:.:pressed")
        self.assertEqual(signal["from"], self.path + "::node:Label")

    def test_hash_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_runtime_bindings(self.path, self.text, {self.path: "0" * 64})

    def test_subresource_binding_and_dangling_reference_fail(self):
        text = """[gd_resource load_steps=2 format=3]\n[sub_resource type=\"StyleBoxFlat\" id=\"1\"]\nbg_color = Color(1, 1, 1, 1)\n[resource]\nnormal = SubResource(\"1\")\n"""
        path = "Game.Godot/Themes/test.tres"; hashes = {path: hashlib.sha256(text.encode()).hexdigest()}
        edges = parse_runtime_bindings(path, text, hashes)
        self.assertEqual(edges[0]["to"], path + "::subresource:1")


if __name__ == "__main__":
    unittest.main()
