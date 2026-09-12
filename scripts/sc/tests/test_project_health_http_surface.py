#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from _project_health_http import handler_factory


class ProjectHealthHttpSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(ROOT))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(
        self,
        method: str,
        path: str,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, dict[str, str]]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read().decode("utf-8")
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        status = response.status
        connection.close()
        return status, payload, response_headers

    def test_knowledge_page_assets_and_session_are_reachable(self) -> None:
        status, payload, _ = self.request("GET", "/api/knowledge/session")
        self.assertEqual(200, status)
        session = json.loads(payload)
        self.assertEqual("project-health-knowledge-v1", session["service"])
        self.assertTrue(session["token"])

        status, html, headers = self.request("GET", "/knowledge")
        self.assertEqual(200, status)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Knowledge", html)

        status, javascript, headers = self.request("GET", "/knowledge/app.js")
        self.assertEqual(200, status)
        self.assertIn("javascript", headers.get("content-type", ""))
        self.assertIn("'use strict'", javascript)

        status, stylesheet, headers = self.request("GET", "/knowledge/style.css")
        self.assertEqual(200, status)
        self.assertIn("text/css", headers.get("content-type", ""))
        self.assertTrue(stylesheet.strip())

    def test_loopback_host_and_csrf_boundaries_fail_closed(self) -> None:
        status, _, _ = self.request("GET", "/api/knowledge/session", headers={"Host": "evil.example"})
        self.assertEqual(403, status)

        status, _, _ = self.request(
            "POST",
            "/api/knowledge/scan",
            body="{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(403, status)


if __name__ == "__main__":
    unittest.main()
