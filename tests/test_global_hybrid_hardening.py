"""Behavioral RED tests for the global-hybrid Jev boundary.

These tests deliberately exercise the public contract that must hold before the
adapter is installed globally or used for live requests.  They use temporary
state and synthetic responses only; no credential or network call is used.
"""
from __future__ import annotations

import gc
import importlib.util
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import tomllib

from jevkit.authorization import CallBudget
from jevkit.engine import ROOT, fixture, questions_for, simulated_response, spec
from jevkit.security import SafeError


def load_bootstrap():
    path = ROOT / "scripts" / "bootstrap.py"
    module_spec = importlib.util.spec_from_file_location("jev_bootstrap_hardening", path)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def init_repo(path: Path) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=path, check=True)
    (path / "baseline.txt").write_text("baseline\n")
    subprocess.run(["git", "add", "baseline.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=path, check=True)


class GlobalHybridHardeningTests(unittest.TestCase):
    def context(self, state_root: Path, scope: str, workspace: Path | None = None):
        from jevkit.runtime import RuntimeContext

        return RuntimeContext(ROOT, state_root, scope, workspace)

    def test_mcp_defaults_to_global_offline_and_hides_live_evaluate(self):
        from jevkit import mcp_server

        with tempfile.TemporaryDirectory() as tmp:
            tools = mcp_server.tools(state_root=Path(tmp) / "state")
        names = {tool["name"] for tool in tools}
        self.assertEqual(
            names,
            {
                "jev_health",
                "jev_policy_status",
                "jev_policy_check",
                "jev_catalog",
                "jev_describe",
                "jev_run_fixture",
            },
        )
        self.assertNotIn("jev_evaluate", names)

    def test_project_live_without_workspace_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SafeError, "WORKSPACE_ID_REQUIRED"):
                self.context(Path(tmp) / "state", "project-live")

    def test_bootstrap_args_pin_scope_and_canonical_workspace(self):
        bootstrap = load_bootstrap()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / ".codex").mkdir()
            bootstrap.configure(root, Path("/opt/jev/bin/python").resolve())
            config = tomllib.loads((root / ".codex" / "config.toml").read_text())
            args = config["mcp_servers"]["jev_control"]["args"]
            self.assertIn("--scope", args)
            self.assertEqual(args[args.index("--scope") + 1], "project-live")
            self.assertIn("--workspace", args)
            self.assertEqual(args[args.index("--workspace") + 1], str(root))

    def test_default_state_root_is_portable_and_outside_package(self):
        from jevkit.runtime import GLOBAL_OFFLINE

        parameter = inspect.signature(__import__("jevkit.runtime", fromlist=["RuntimeContext"]).RuntimeContext).parameters["state_root"]
        self.assertIsNot(parameter.default, inspect.Parameter.empty)
        private_test_root = ROOT / ".local"
        private_test_root.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_test_root) as tmp:
            nested = Path(tmp) / "nested"
            with self.assertRaisesRegex(SafeError, "STATE_ROOT_INSIDE_PACKAGE"):
                self.context(nested, GLOBAL_OFFLINE)

    def test_explicit_symlink_state_root_is_rejected_before_resolution(self):
        from jevkit.runtime import GLOBAL_OFFLINE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "real-state"
            target.mkdir()
            link = root / "linked-state"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(SafeError, "UNSAFE_PATH"):
                self.context(link, GLOBAL_OFFLINE)

    def test_grant_from_workspace_a_cannot_authorize_workspace_b(self):
        from jevkit.runtime import PROJECT_LIVE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root / "repo-a")
            init_repo(root / "repo-b")
            a = self.context(root / "state", PROJECT_LIVE, root / "repo-a")
            b = self.context(root / "state", PROJECT_LIVE, root / "repo-b")
            a.create_live_grant(calls=1, minutes=1)
            self.assertFalse(b.read_live_grant()["enabled"])
            with self.assertRaisesRegex(SafeError, "LIVE_NOT_AUTHORIZED"):
                CallBudget(self.context(root / "state", PROJECT_LIVE, root / "repo-b").package_root,
                           storage_root=b.grant_root).reserve(False)

    def test_revision_fingerprint_changes_with_reviewed_worktree(self):
        from jevkit.runtime import PROJECT_LIVE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=repo, check=True)
            source = repo / "source.txt"
            source.write_text("reviewed\n")
            subprocess.run(["git", "add", "source.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "reviewed baseline"], cwd=repo, check=True)
            before = self.context(root / "state", PROJECT_LIVE, repo)
            source.write_text("changed after grant\n")
            after = self.context(root / "state", PROJECT_LIVE, repo)
            self.assertNotEqual(before.revision, after.revision)

    def test_same_context_rejects_live_after_workspace_change(self):
        from jevkit.runtime import PROJECT_LIVE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=repo, check=True)
            source = repo / "source.txt"
            source.write_text("reviewed\n")
            subprocess.run(["git", "add", "source.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "reviewed baseline"], cwd=repo, check=True)
            ctx = self.context(root / "state", PROJECT_LIVE, repo)
            ctx.create_live_grant(calls=1, minutes=1)
            source.write_text("changed after grant\n")
            with patch("jevkit.client.evaluate") as evaluate:
                with self.assertRaisesRegex(SafeError, "WORKSPACE_REVISION_CHANGED"):
                    ctx.evaluate("01-skill-routing")
                evaluate.assert_not_called()

    def test_project_live_rejects_missing_workspace_directory(self):
        from jevkit.runtime import PROJECT_LIVE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(SafeError, "WORKSPACE_DIRECTORY_REQUIRED"):
                self.context(root / "state", PROJECT_LIVE, root / "missing")

    def test_legacy_grant_ledger_is_invalidated_before_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_root = root / ".local"
            ledger_root.mkdir(mode=0o700)
            ledger = ledger_root / "live-grants.sqlite3"
            connection = sqlite3.connect(ledger)
            try:
                connection.execute(
                    "CREATE TABLE grants (id TEXT PRIMARY KEY, expires REAL, max_calls INTEGER, used INTEGER, allow_custom INTEGER)"
                )
                connection.execute(
                    "INSERT INTO grants VALUES ('legacy', 9999999999, 99, 0, 1)"
                )
                connection.commit()
            finally:
                connection.close()
            ledger.chmod(0o600)
            budget = CallBudget(root)
            self.assertFalse(budget.status()["enabled"])
            status = budget.grant(1, 1)
            self.assertTrue(status["enabled"])
            self.assertNotEqual(status["grant_id"], "legacy")

    def test_global_fixture_does_not_persist_shared_receipt(self):
        from jevkit.runtime import GLOBAL_OFFLINE

        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp) / "state", GLOBAL_OFFLINE)
            record = ctx.run_fixture("01-skill-routing", "nominal")
            self.assertNotIn("receipt_path", record)
            self.assertEqual(list(ctx.evidence_root.rglob("*.json")), [])

    def test_rollback_revokes_workspace_scoped_grant_even_when_revision_is_stale(self):
        from jevkit.runtime import PROJECT_LIVE, revoke_workspace_grant

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            init_repo(repo)
            state_root = root / "state"
            ctx = self.context(state_root, PROJECT_LIVE, repo)
            ctx.create_live_grant(calls=1, minutes=1)
            (repo / "baseline.txt").write_text("changed after grant\n")
            revoke_workspace_grant(ROOT, repo, state_root)
            fresh = self.context(state_root, PROJECT_LIVE, repo)
            self.assertFalse(fresh.read_live_grant()["enabled"])

    def test_cli_custom_live_accepts_required_metadata_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            init_repo(repo)
            state_file = root / "state.json"
            state_file.write_text(json.dumps(fixture("01-skill-routing")["state"]))
            environment = os.environ.copy()
            environment["JEV_PROVIDER"] = "typesafe"
            environment["TYPESAFE_API_KEY"] = "synthetic-local-credential"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "jev.py"),
                    "run",
                    "01-skill-routing",
                    "--mode",
                    "live",
                    "--scope",
                    "project-live",
                    "--workspace",
                    str(repo),
                    "--state-root",
                    str(root / "runtime-state"),
                    "--state",
                    str(state_file),
                    "--request-id",
                    "cli-contract-test",
                    "--data-classification",
                    "internal-minimized",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("REQUEST_GRANT_REQUIRED", result.stderr)
            self.assertNotIn("unrecognized arguments", result.stderr)

    def test_live_custom_requests_require_classification_and_exact_request_grant(self):
        from jevkit.runtime import PROJECT_LIVE

        state = fixture("01-skill-routing")["state"]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "repo"
            init_repo(workspace)
            ctx = self.context(Path(tmp) / "state", PROJECT_LIVE, workspace)
            parameters = inspect.signature(ctx.evaluate).parameters
            for name in ("request_id", "data_classification"):
                self.assertIn(name, parameters)
            with patch.dict(os.environ, {"JEV_PROVIDER": "typesafe", "TYPESAFE_API_KEY": "synthetic-local-credential"}):
                with self.assertRaisesRegex(SafeError, "CLASSIFICATION_REQUIRED"):
                    ctx.evaluate("01-skill-routing", state=state, request_id="req-1")
                with self.assertRaisesRegex(SafeError, "DATA_CLASSIFICATION_NOT_ALLOWED"):
                    ctx.evaluate(
                        "01-skill-routing",
                        state=state,
                        request_id="req-1",
                        data_classification="restricted",
                    )
                with self.assertRaisesRegex(SafeError, "REQUEST_GRANT_REQUIRED"):
                    ctx.evaluate(
                        "01-skill-routing",
                        state=state,
                        request_id="req-1",
                        data_classification="internal-minimized",
                    )

    def test_receipts_bind_workspace_revision_adapter_grant_and_content_hash(self):
        from jevkit.runtime import PROJECT_LIVE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_repo(root / "repo")
            ctx = self.context(root / "state", PROJECT_LIVE, root / "repo")
            ctx.create_live_grant(calls=1, minutes=1)
            case = fixture("01-skill-routing")
            questions = questions_for(spec(case["case_id"]), case["state"])
            response = simulated_response(questions, case["mock_values"])
            response["model"] = "jev-1.13.0"
            with patch("jevkit.client.evaluate", return_value=response):
                record = ctx.evaluate(case["case_id"], state=None)
            receipt = Path(record["receipt_path"])
            persisted = json.loads(receipt.read_text())
            for key in ("workspace_id", "revision", "adapter_version", "grant_id", "record_sha256"):
                self.assertIn(key, persisted)
            self.assertEqual(persisted["record_sha256"], record["record_sha256"])
            self.assertNotEqual(receipt, Path(record["receipt_path"]).with_name("overwrite.json"))
            with self.assertRaises(FileExistsError):
                receipt.open("x").close()

    def test_call_budget_closes_connections_across_repeated_lifecycle_calls(self):
        # Keep the temporary path under the project-local private root because
        # macOS's /private/var symlinked temp hierarchy is intentionally rejected
        # by the package's private_dir boundary checks.
        private_test_root = ROOT / ".local"
        private_test_root.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_test_root) as tmp:
            budget = CallBudget(Path(tmp))
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                for _ in range(25):
                    budget.grant(2, 1)
                    budget.status()
                    budget.revoke()
                gc.collect()
            self.assertFalse(
                [warning for warning in caught if issubclass(warning.category, ResourceWarning)],
                "CallBudget leaked an sqlite connection",
            )


if __name__ == "__main__":
    unittest.main()
