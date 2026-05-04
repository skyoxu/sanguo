#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contracts_check = _load_module("check_domain_contracts_module", "scripts/python/check_domain_contracts.py")


class CheckDomainContractsTests(unittest.TestCase):
    def test_should_resolve_eventtypes_symbol_and_match_nearest_doc_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contracts_dir = root / "Game.Core" / "Contracts"
            contracts_dir.mkdir(parents=True, exist_ok=True)
            (contracts_dir / "EventTypes.cs").write_text(
                "namespace Game.Core.Contracts;\n"
                "public static class EventTypes\n"
                "{\n"
                "    public const string Guild_Created = \"core.guild_created.spawned\";\n"
                "}\n",
                encoding="utf-8",
            )
            (contracts_dir / "GuildEvents.cs").write_text(
                "namespace Game.Core.Contracts;\n"
                "/// <summary>Guild created.</summary>\n"
                "/// <remarks>Domain event: core.guild.created</remarks>\n"
                "public sealed record GuildCreated\n"
                "{\n"
                "    public const string EventType = \"core.guild.created\";\n"
                "}\n"
                "/// <summary>Guild spawned.</summary>\n"
                "/// <remarks>Domain event: core.guild_created.spawned</remarks>\n"
                "public sealed record GuildSpawned\n"
                "{\n"
                "    public const string EventType = EventTypes.Guild_Created;\n"
                "}\n",
                encoding="utf-8",
            )
            out_path = root / "out.json"

            with mock.patch.object(contracts_check, "repo_root", return_value=root):
                argv = [
                    "check_domain_contracts.py",
                    "--contracts-dir",
                    "Game.Core/Contracts",
                    "--out",
                    str(out_path),
                ]
                with mock.patch.object(sys, "argv", argv):
                    rc = contracts_check.main()

            self.assertEqual(0, rc)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])
            self.assertEqual(2, payload["counts"]["event_type_constants"])
            self.assertEqual(0, payload["counts"]["warnings"])
            self.assertEqual(
                ["core.guild.created", "core.guild_created.spawned"],
                sorted(item["event_type"] for item in payload["findings"]),
            )

    def test_should_fail_when_eventtypes_symbol_is_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contracts_dir = root / "Game.Core" / "Contracts"
            contracts_dir.mkdir(parents=True, exist_ok=True)
            (contracts_dir / "BrokenEvent.cs").write_text(
                "namespace Game.Core.Contracts;\n"
                "public sealed record BrokenEvent\n"
                "{\n"
                "    public const string EventType = EventTypes.UnknownValue;\n"
                "}\n",
                encoding="utf-8",
            )
            out_path = root / "out.json"

            with mock.patch.object(contracts_check, "repo_root", return_value=root):
                argv = [
                    "check_domain_contracts.py",
                    "--contracts-dir",
                    "Game.Core/Contracts",
                    "--out",
                    str(out_path),
                ]
                with mock.patch.object(sys, "argv", argv):
                    rc = contracts_check.main()

            self.assertEqual(1, rc)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual("fail", payload["status"])
            self.assertIn("unresolved EventTypes symbol: UnknownValue", payload["findings"][0]["issues"])


if __name__ == "__main__":
    unittest.main()
