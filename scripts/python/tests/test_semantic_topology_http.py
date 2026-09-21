from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/python"))

from _project_health_http import handler_factory
from project_health_knowledge import base_dir, write_json


class SemanticTopologyHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path: str) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", path)
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, body

    def test_topology_page_is_available_without_generated_topology(self):
        status, body = self.request("/knowledge/topology")
        self.assertEqual(200, status)
        self.assertIn(b"Design", body)
        status, body = self.request("/api/knowledge/topology?mode=main")
        self.assertEqual(200, status)
        payload = json.loads(body)
        self.assertFalse(payload["available"])
        self.assertEqual("legacy_unmapped", payload["status"])
        self.assertEqual("main", payload["identity"]["kind"])

    def test_workspace_stabilized_view_is_addressable(self):
        write_json(base_dir(self.root) / "topology/workspace-latest-stabilized.json", {
            "schema_version": "newrouge.semantic-topology-view.v1",
            "available": True,
            "fresh": True,
            "identity": {"kind": "workspace", "revision": "workspace:chapter5", "trigger_run_id": "ch5"},
            "status": "fresh",
            "nodes": {"source_blocks": [], "requirements": [], "capabilities": [], "tasks": [], "acceptance": []},
            "edges": [], "task_trace": {}, "summary": {}, "problems": [],
        })
        status, body = self.request("/api/knowledge/topology?mode=workspace&view=stabilized")
        self.assertEqual(200, status)
        payload = json.loads(body)
        self.assertEqual("stabilized", payload["workspace_view"])
        self.assertEqual("ch5", payload["identity"]["trigger_run_id"])

    def test_workspace_preview_is_separate_from_main(self):
        write_json(base_dir(self.root) / "topology/workspace-latest.json", {
            "schema_version": "newrouge.semantic-topology-view.v1",
            "available": True,
            "fresh": True,
            "identity": {"kind": "workspace", "revision": "workspace:test"},
            "status": "fresh",
            "nodes": {
                "source_blocks": [], "requirements": [], "capabilities": [],
                "tasks": [], "acceptance": [],
            },
            "edges": [],
            "task_trace": {},
            "summary": {},
            "problems": [],
        })
        status, body = self.request("/api/knowledge/topology?mode=workspace")
        self.assertEqual(200, status)
        workspace = json.loads(body)
        self.assertEqual("workspace", workspace["identity"]["kind"])
        self.assertEqual("workspace:test", workspace["identity"]["revision"])

        status, body = self.request("/api/knowledge/topology?mode=main")
        self.assertEqual(200, status)
        main = json.loads(body)
        self.assertEqual("main", main["identity"]["kind"])
        self.assertNotEqual(workspace["identity"], main["identity"])


if __name__ == "__main__":
    unittest.main()
