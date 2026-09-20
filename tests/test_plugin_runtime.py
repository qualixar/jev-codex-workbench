"""Installed-plugin contract for the global gated-live Jev MCP."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from jevkit.engine import ROOT


PLUGIN = ROOT / "plugins" / "qualixar-jev-control"


class PluginRuntimeTests(unittest.TestCase):
    def test_release_is_policy_mode_patch_version(self):
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["version"], "1.1.1")
        self.assertTrue((PLUGIN / "hooks" / "hooks.json").is_file())
        self.assertTrue((PLUGIN / "hooks" / "jev_policy_hook.py").is_file())

    def test_release_manifest_contains_only_clean_checkout_files(self):
        manifest = json.loads((ROOT / "MANIFEST.json").read_text())
        tracked = set(
            subprocess.run(
                ["git", "ls-files"],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.splitlines()
        )
        self.assertTrue(set(manifest["files"]).issubset(tracked))
        for path in manifest["files"]:
            self.assertNotIn(".mypy_cache", path)
            self.assertNotIn(".ruff_cache", path)
            self.assertFalse(path.startswith(".codex/"))

    def test_runtime_manifest_matches_every_bundled_file(self):
        runtime = PLUGIN / "runtime"
        manifest = json.loads((runtime / "RUNTIME_MANIFEST.json").read_text())
        self.assertEqual(manifest["mode"], "global-hybrid")
        self.assertTrue(manifest["live_evaluation_exposed"])
        self.assertFalse(manifest["credential_forwarding_configured"])
        actual = {
            str(path.relative_to(runtime)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in runtime.rglob("*")
            if path.is_file() and path.name != "RUNTIME_MANIFEST.json"
        }
        self.assertEqual(actual, manifest["files"])
        self.assertIn("jevkit/client.py", actual)
        self.assertIn("jevkit/authorization.py", actual)
        self.assertIn("jevkit/credentials.py", actual)
        self.assertIn("jevkit/providers.py", actual)
        build_mode = (runtime / "jevkit" / "build_mode.py").read_text()
        self.assertIn("OFFLINE_ONLY = False", build_mode)

    def test_bundled_cli_requires_human_grant_before_live_request(self):
        runtime = PLUGIN / "runtime"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=repo, check=True)
            (repo / "baseline.txt").write_text("baseline\n")
            subprocess.run(["git", "add", "baseline.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)
            environment = os.environ.copy()
            environment["JEV_PROVIDER"] = "typesafe"
            environment["TYPESAFE_API_KEY"] = "must-not-be-read-or-echoed"
            environment["XDG_STATE_HOME"] = str(Path(tmp) / "state")
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [
                    "python3",
                    str(runtime / "jev.py"),
                    "run",
                    "01-skill-routing",
                    "--mode",
                    "live",
                    "--scope",
                    "global-hybrid",
                    "--workspace",
                    str(repo),
                ],
                cwd=repo,
                env=environment,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("LIVE_NOT_AUTHORIZED", result.stderr)
            self.assertNotIn("must-not-be-read-or-echoed", result.stderr)

    def test_launcher_exposes_gated_live_tool_from_unrelated_workspaces(self):
        launcher = PLUGIN / "scripts" / "launch-jev-global-hybrid"
        self.assertIn("sys.version_info >= (3, 11)", launcher.read_text())
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "plugin-test", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "jev_health", "arguments": {}},
            },
        ]
        payload = "\n".join(json.dumps(message) for message in messages) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            outputs = []
            for name in ("workspace-a", "workspace-b"):
                workspace = root / name
                workspace.mkdir()
                environment = os.environ.copy()
                environment.update(
                    {
                        "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
                        "XDG_STATE_HOME": str(state),
                        "JEV_PROVIDER": "typesafe",
                        "TYPESAFE_API_KEY": "must-not-be-read-or-echoed",
                    }
                )
                result = subprocess.run(
                    [str(launcher)],
                    cwd=workspace,
                    env=environment,
                    input=payload,
                    text=True,
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                outputs.append([json.loads(line) for line in result.stdout.splitlines()])
            for rows in outputs:
                names = {tool["name"] for tool in rows[1]["result"]["tools"]}
                self.assertEqual(
                    names,
                    {
                        "jev_health",
                        "jev_catalog",
                        "jev_describe",
                        "jev_run_fixture",
                        "jev_evaluate",
                        "jev_policy_status",
                        "jev_policy_check",
                    },
                )
                health = json.loads(rows[2]["result"]["content"][0]["text"])
                self.assertEqual(health["scope"], "global-hybrid")
                self.assertTrue(health["credential_available"])
                self.assertFalse(health["live_grant_checked"])
                self.assertNotIn("must-not-be-read-or-echoed", result.stdout)


if __name__ == "__main__":
    unittest.main()
