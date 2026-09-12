import json, subprocess, unittest
from pathlib import Path
from scripts.python.knowledge_binding_producer import produce_binding, validate_binding_evidence

ROOT=Path(__file__).resolve().parents[3]
class FreezeBindingIntegrationTests(unittest.TestCase):
    def test_chapter6_shadow_decisions_produce_verified_evidence(self):
        bundle=json.loads((ROOT/'logs/ci/knowledge-context/chapter6-T29-GM-0129-v2.json').read_text(encoding='utf-8'))
        decisions=json.loads((ROOT/'logs/ci/knowledge-context/chapter6-T29-GM-0129-v2.decisions.json').read_text(encoding='utf-8'))
        evidence=produce_binding(ROOT,bundle,decisions)
        validate_binding_evidence(ROOT,bundle,evidence)
        self.assertEqual(evidence['repository_revision'],bundle['snapshot']['commit'])
        self.assertGreater(len(evidence['evidence']),0)
