#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


review_cli = _load_module("sc_llm_review_cli_module", "scripts/sc/_llm_review_cli.py")


class LlmReviewBackendCliTests(unittest.TestCase):
    def test_resolve_agents_should_preserve_explicit_agent_list_without_auto_adding_semantic_reviewer(self) -> None:
        agents = review_cli.resolve_agents("code-reviewer,security-auditor", "warn")

        self.assertEqual(["code-reviewer", "security-auditor"], agents)

    def test_resolve_agents_should_add_semantic_reviewer_when_using_profile_defaults(self) -> None:
        agents = review_cli.resolve_agents("", "warn")

        self.assertIn("semantic-equivalence-auditor", agents)

    def test_apply_delivery_profile_defaults_should_resolve_llm_backend(self) -> None:
        args = Namespace(
            delivery_profile="fast-ship",
            llm_backend=None,
            agents="",
            diff_mode="full",
            timeout_sec=900,
            agent_timeout_sec=300,
            semantic_gate="skip",
            strict=False,
            model_reasoning_effort="low",
            prompt_budget_gate="warn",
        )
        with mock.patch.object(review_cli, "resolve_llm_backend", return_value="codex-cli"):
            updated = review_cli.apply_delivery_profile_defaults(args)

        self.assertEqual("codex-cli", updated.llm_backend)

    def test_validate_args_should_fail_when_openai_backend_missing_requirements(self) -> None:
        args = Namespace(
            uncommitted=False,
            commit=None,
            auto_commit=False,
            task_id=None,
            timeout_sec=900,
            agent_timeout_sec=300,
            prompt_max_chars=32000,
            self_check=True,
            dry_run_plan=False,
            prompts_only=False,
            llm_backend="openai-api",
        )
        with mock.patch.object(
            review_cli,
            "inspect_llm_backend",
            return_value={
                "backend": "openai-api",
                "available": False,
                "blocking_errors": ["python package 'openai' is not installed", "OPENAI_API_KEY is not set"],
            },
        ):
            errors = review_cli.validate_args(args)

        self.assertIn("python package 'openai' is not installed", errors)
        self.assertIn("OPENAI_API_KEY is not set", errors)
        self.assertEqual("openai-api", args._llm_backend_info["backend"])

    def test_validate_args_should_allow_prompts_only_even_when_backend_not_ready(self) -> None:
        args = Namespace(
            uncommitted=False,
            commit=None,
            auto_commit=False,
            task_id=None,
            timeout_sec=900,
            agent_timeout_sec=300,
            prompt_max_chars=32000,
            self_check=False,
            dry_run_plan=False,
            prompts_only=True,
            llm_backend="openai-api",
        )
        with mock.patch.object(
            review_cli,
            "inspect_llm_backend",
            return_value={
                "backend": "openai-api",
                "available": False,
                "blocking_errors": ["python package 'openai' is not installed", "OPENAI_API_KEY is not set"],
            },
        ):
            errors = review_cli.validate_args(args)

        self.assertEqual([], errors)

    def test_validate_args_should_fail_when_semantic_gate_require_omits_semantic_reviewer_from_explicit_agents(self) -> None:
        args = Namespace(
            uncommitted=False,
            commit=None,
            auto_commit=False,
            task_id=None,
            timeout_sec=900,
            agent_timeout_sec=300,
            prompt_max_chars=32000,
            self_check=True,
            dry_run_plan=False,
            prompts_only=False,
            llm_backend="codex-cli",
            agents="code-reviewer,security-auditor",
            semantic_gate="require",
            _agents_explicit=True,
        )
        with mock.patch.object(
            review_cli,
            "inspect_llm_backend",
            return_value={
                "backend": "codex-cli",
                "available": True,
                "blocking_errors": [],
            },
        ):
            errors = review_cli.validate_args(args)

        self.assertTrue(any("semantic-equivalence-auditor" in item for item in errors))

    def test_summary_base_should_include_backend_readiness(self) -> None:
        args = Namespace(
            strict=False,
            prompt_max_chars=32000,
            prompt_budget_gate="warn",
            llm_backend="codex-cli",
            _llm_backend_info={
                "backend": "codex-cli",
                "available": True,
                "blocking_errors": [],
                "executable": "codex",
            },
        )

        summary = review_cli.summary_base(
            mode="self-check",
            out_dir=REPO_ROOT / "logs" / "ci" / "tmp",
            args=args,
            security_profile="host-safe",
            status="ok",
        )

        self.assertEqual("codex-cli", (summary.get("llm_backend") or {}).get("backend"))
        self.assertTrue(bool((summary.get("llm_backend") or {}).get("available")))


if __name__ == "__main__":
    unittest.main()
