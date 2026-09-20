"""RED tests for the global/offline + project/live Jev runtime boundary.

These tests intentionally describe the public runtime contract before its
implementation exists.  They must remain independent of the user's real
credential and never make a network call.
"""
from __future__ import annotations

import json
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jevkit.authorization import CallBudget
from jevkit.client import evaluate
from jevkit.engine import ROOT, fixture, questions_for, simulated_response, spec
from jevkit.providers import provider_profile
from jevkit.security import SafeError


def init_repo(path: Path) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=path, check=True)
    (path / "baseline.txt").write_text("baseline\n")
    subprocess.run(["git", "add", "baseline.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=path, check=True)


class GlobalHybridRuntimeTests(unittest.TestCase):
    def make_context(self, root: Path, scope: str, workspace: Path | None = None):
        # Imported lazily so each behavior reports the missing runtime contract
        # as its own RED failure instead of aborting test discovery.
        from jevkit.runtime import RuntimeContext

        return RuntimeContext(
            package_root=ROOT,
            state_root=root / "state",
            scope=scope,
            workspace_root=workspace,
        )

    def test_global_offline_exposes_only_safe_offline_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_context(Path(tmp), "global-offline")
            self.assertEqual(
                set(ctx.tool_names()),
                {"jev_health", "jev_catalog", "jev_describe", "jev_run_fixture"},
            )
            self.assertNotIn("jev_evaluate", ctx.tool_names())
            self.assertNotIn("jev_grant", ctx.tool_names())
            self.assertNotIn("jev_read_grant", ctx.tool_names())

    def test_global_offline_cannot_create_or_read_live_grants(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_context(Path(tmp), "global-offline")
            with self.assertRaisesRegex(SafeError, "LIVE_SCOPE_REQUIRED"):
                ctx.create_live_grant(calls=1, minutes=1)
            with self.assertRaisesRegex(SafeError, "LIVE_SCOPE_REQUIRED"):
                ctx.read_live_grant()

    def test_project_live_exposes_evaluate_but_requires_workspace_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(SafeError, "WORKSPACE_ID_REQUIRED"):
                self.make_context(root, "project-live")
            init_repo(root / "repo-a")
            ctx = self.make_context(root, "project-live", root / "repo-a")
            self.assertIn("jev_evaluate", ctx.tool_names())
            self.assertNotIn("jev_grant", ctx.tool_names())
            self.assertNotIn("jev_read_grant", ctx.tool_names())

    def test_canonical_workspaces_have_distinct_private_state_grant_and_evidence_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root / "repo-a")
            init_repo(root / "repo-b")
            a = self.make_context(root, "project-live", root / "repo-a")
            b = self.make_context(root, "project-live", root / "repo-b")
            self.assertNotEqual(a.state_root, b.state_root)
            self.assertNotEqual(a.grant_root, b.grant_root)
            self.assertNotEqual(a.evidence_root, b.evidence_root)
            for path in (a.state_root, a.grant_root, a.evidence_root):
                self.assertFalse(path.is_symlink())

    def test_receipts_are_written_under_state_not_package_code_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root / "repo")
            ctx = self.make_context(root / "state", "project-live", root / "repo")
            receipt = ctx.run_fixture("01-skill-routing", "nominal")
            receipt_path = Path(receipt["receipt_path"])
            self.assertTrue(receipt_path.is_file())
            self.assertTrue(receipt_path.is_relative_to(ctx.state_root))
            self.assertFalse(receipt_path.is_relative_to(ROOT))
            self.assertFalse((ROOT / "artifacts" / "runs" / receipt_path.name).exists())
            json.loads(receipt_path.read_text())

    def test_live_response_model_must_equal_requested_pin(self):
        from jevkit.contract import validate_response_model

        response = {
            "model": "jev-1.13.0-other",
            "answers": {},
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        with self.assertRaisesRegex(SafeError, "MODEL_ID_MISMATCH"):
            validate_response_model(response, requested_model="jev-1.13.0")
        response["model"] = "jev-1.13.0"
        self.assertIs(validate_response_model(response, requested_model="jev-1.13.0"), response)

    def test_live_client_rejects_fixture_model_from_injected_transport(self):
        case = fixture("01-skill-routing")
        questions = questions_for(spec(case["case_id"]), case["state"])
        response = simulated_response(questions, case["mock_values"])
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"JEV_PROVIDER": "typesafe", "TYPESAFE_API_KEY": "synthetic-local-credential"}
        ):
            root = Path(tmp)
            profile = provider_profile("typesafe")
            CallBudget(root, provider_id=profile.provider_id,
                       provider_profile_sha256=profile.profile_sha256).grant(1, 1)

            def transport(*_args, **_kwargs):
                return io.BytesIO(json.dumps(response).encode())

            with self.assertRaisesRegex(SafeError, "MODEL_ID_MISMATCH"):
                evaluate(root, case["state"], questions, False, transport=transport)


if __name__ == "__main__":
    unittest.main()
