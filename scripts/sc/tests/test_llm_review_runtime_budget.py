#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
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


review_engine = _load_module("sc_llm_review_engine_budget_module", "scripts/sc/_llm_review_engine.py")


class LlmReviewRuntimeBudgetTests(unittest.TestCase):
    def _run_main_with_time_budget(
        self,
        *,
        agents: str,
        monotonic_values: list[float],
    ) -> tuple[int, list[int], dict]:
        observed_timeouts: list[int] = []
        monotonic_iter = iter(monotonic_values)

        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            temp_root = Path(td)
            out_dir = temp_root / "logs" / "ci" / "sc-llm-review"
            out_dir.mkdir(parents=True, exist_ok=True)

            def fake_run_codex_exec(*, backend: str, prompt: str, output_last_message: Path, timeout_sec: int, codex_configs=None):  # noqa: ANN001
                observed_timeouts.append(int(timeout_sec))
                output_last_message.parent.mkdir(parents=True, exist_ok=True)
                output_last_message.write_text("VERDICT: OK\n", encoding="utf-8")
                return 0, "trace ok\n", [str(backend), "fake-model"]

            argv = [
                "llm_review.py",
                "--agents",
                agents,
                "--timeout-sec",
                "200",
                "--agent-timeout-sec",
                "180",
                "--llm-backend",
                "codex-cli",
                "--diff-mode",
                "summary",
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(review_engine, "apply_delivery_profile_defaults", side_effect=lambda args: args), \
                mock.patch.object(review_engine, "validate_args", return_value=[]), \
                mock.patch.object(review_engine, "ci_dir", return_value=out_dir), \
                mock.patch.object(review_engine, "repo_root", return_value=temp_root), \
                mock.patch.object(review_engine, "build_diff_context", return_value="## Diff\nshort\n"), \
                mock.patch.object(review_engine, "resolve_threat_model", return_value="singleplayer"), \
                mock.patch.object(review_engine, "build_threat_model_context", return_value=""), \
                mock.patch.object(review_engine, "build_security_profile_context", return_value=""), \
                mock.patch.object(review_engine, "agent_prompt", return_value=("Role prompt", {"agent_prompt_source": "inline"})), \
                mock.patch.object(review_engine, "run_codex_exec", side_effect=fake_run_codex_exec), \
                mock.patch.object(review_engine.time, "monotonic", side_effect=lambda: next(monotonic_iter)):
                rc = review_engine.main()

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            return rc, observed_timeouts, summary

    def test_main_should_allow_started_reviewer_to_use_full_agent_timeout_even_when_total_budget_remaining_is_smaller(self) -> None:
        rc, observed_timeouts, summary = self._run_main_with_time_budget(
            agents="code-reviewer,security-auditor",
            monotonic_values=[0.0, 0.0, 170.0],
        )

        self.assertEqual(0, rc)
        self.assertEqual([180, 180], observed_timeouts)
        self.assertEqual("ok", summary["status"])
        self.assertEqual(
            ["code-reviewer", "security-auditor"],
            [str(item.get("agent") or "") for item in summary["results"]],
        )
        self.assertEqual(30, int((summary["results"][1].get("details") or {}).get("remaining_before_sec") or 0))

    def test_main_should_skip_only_reviewers_not_yet_started_after_total_budget_is_exhausted(self) -> None:
        rc, observed_timeouts, summary = self._run_main_with_time_budget(
            agents="code-reviewer,security-auditor,test-automator",
            monotonic_values=[0.0, 0.0, 170.0, 205.0],
        )

        self.assertEqual(0, rc)
        self.assertEqual([180, 180], observed_timeouts)
        self.assertEqual("warn", summary["status"])
        self.assertEqual("skipped", summary["results"][2]["status"])
        self.assertEqual(124, summary["results"][2]["rc"])
        self.assertIn("total timeout budget exhausted", str((summary["results"][2].get("details") or {}).get("note") or "").lower())
        self.assertEqual(30, int((summary["results"][1].get("details") or {}).get("remaining_before_sec") or 0))

    def test_main_should_defer_semantic_reviewer_until_other_reviewers_finish_clean(self) -> None:
        observed_agents: list[str] = []
        monotonic_iter = iter([0.0, 0.0, 10.0, 20.0])

        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            temp_root = Path(td)
            out_dir = temp_root / "logs" / "ci" / "sc-llm-review"
            out_dir.mkdir(parents=True, exist_ok=True)

            def fake_run_codex_exec(*, backend: str, prompt: str, output_last_message: Path, timeout_sec: int, codex_configs=None):  # noqa: ANN001
                agent = output_last_message.stem.replace("review-", "")
                observed_agents.append(agent)
                output_last_message.parent.mkdir(parents=True, exist_ok=True)
                output_last_message.write_text("VERDICT: OK\n", encoding="utf-8")
                return 0, "trace ok\n", [str(backend), "fake-model"]

            argv = [
                "llm_review.py",
                "--agents",
                "code-reviewer,semantic-equivalence-auditor,security-auditor",
                "--timeout-sec",
                "200",
                "--agent-timeout-sec",
                "180",
                "--llm-backend",
                "codex-cli",
                "--diff-mode",
                "summary",
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(review_engine, "apply_delivery_profile_defaults", side_effect=lambda args: args), \
                mock.patch.object(review_engine, "validate_args", return_value=[]), \
                mock.patch.object(review_engine, "ci_dir", return_value=out_dir), \
                mock.patch.object(review_engine, "repo_root", return_value=temp_root), \
                mock.patch.object(review_engine, "build_diff_context", return_value="## Diff\nshort\n"), \
                mock.patch.object(review_engine, "resolve_threat_model", return_value="singleplayer"), \
                mock.patch.object(review_engine, "build_threat_model_context", return_value=""), \
                mock.patch.object(review_engine, "build_security_profile_context", return_value=""), \
                mock.patch.object(review_engine, "agent_prompt", return_value=("Role prompt", {"agent_prompt_source": "inline"})), \
                mock.patch.object(review_engine, "run_codex_exec", side_effect=fake_run_codex_exec), \
                mock.patch.object(review_engine.time, "monotonic", side_effect=lambda: next(monotonic_iter)):
                rc = review_engine.main()

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(0, rc)
            self.assertEqual(
                ["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
                observed_agents,
            )
            self.assertEqual(
                ["primary", "primary", "deferred"],
                [str((item.get("details") or {}).get("execution_stage") or "") for item in summary["results"]],
            )

    def test_main_should_skip_deferred_semantic_when_primary_reviewer_is_not_clean(self) -> None:
        observed_agents: list[str] = []
        monotonic_iter = iter([0.0, 0.0, 10.0])

        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            temp_root = Path(td)
            out_dir = temp_root / "logs" / "ci" / "sc-llm-review"
            out_dir.mkdir(parents=True, exist_ok=True)

            def fake_run_codex_exec(*, backend: str, prompt: str, output_last_message: Path, timeout_sec: int, codex_configs=None):  # noqa: ANN001
                agent = output_last_message.stem.replace("review-", "")
                observed_agents.append(agent)
                output_last_message.parent.mkdir(parents=True, exist_ok=True)
                output_last_message.write_text("", encoding="utf-8")
                return 124, "trace timeout\n", [str(backend), "fake-model"]

            argv = [
                "llm_review.py",
                "--agents",
                "code-reviewer,semantic-equivalence-auditor",
                "--timeout-sec",
                "200",
                "--agent-timeout-sec",
                "180",
                "--llm-backend",
                "codex-cli",
                "--diff-mode",
                "summary",
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(review_engine, "apply_delivery_profile_defaults", side_effect=lambda args: args), \
                mock.patch.object(review_engine, "validate_args", return_value=[]), \
                mock.patch.object(review_engine, "ci_dir", return_value=out_dir), \
                mock.patch.object(review_engine, "repo_root", return_value=temp_root), \
                mock.patch.object(review_engine, "build_diff_context", return_value="## Diff\nshort\n"), \
                mock.patch.object(review_engine, "resolve_threat_model", return_value="singleplayer"), \
                mock.patch.object(review_engine, "build_threat_model_context", return_value=""), \
                mock.patch.object(review_engine, "build_security_profile_context", return_value=""), \
                mock.patch.object(review_engine, "agent_prompt", return_value=("Role prompt", {"agent_prompt_source": "inline"})), \
                mock.patch.object(review_engine, "run_codex_exec", side_effect=fake_run_codex_exec), \
                mock.patch.object(review_engine.time, "monotonic", side_effect=lambda: next(monotonic_iter)):
                rc = review_engine.main()

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            semantic = summary["results"][1]
            self.assertEqual(0, rc)
            self.assertEqual(["code-reviewer"], observed_agents)
            self.assertEqual("skipped", semantic["status"])
            self.assertEqual("deferred", (semantic.get("details") or {}).get("execution_stage"))
            self.assertEqual(
                "deferred_until_prior_reviewers_clean",
                (semantic.get("details") or {}).get("reason_code"),
            )
            self.assertEqual(["code-reviewer"], (semantic.get("details") or {}).get("blocked_by_agents"))


if __name__ == "__main__":
    unittest.main()
