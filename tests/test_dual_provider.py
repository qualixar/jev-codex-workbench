"""Dual-provider and global-live boundary tests.

All credentials are synthetic and all HTTP calls use injected transports.
"""
from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jevkit.authorization import CallBudget
from jevkit.engine import ROOT, fixture, questions_for, simulated_response, spec
from jevkit.security import SafeError


def init_repo(path: Path) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "synthetic@example.invalid"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Synthetic Test"], cwd=path, check=True
    )
    (path / "baseline.txt").write_text("baseline\n")
    subprocess.run(["git", "add", "baseline.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "synthetic baseline"],
        cwd=path,
        check=True,
    )


class ProviderConfigurationTests(unittest.TestCase):
    def test_openrouter_profile_is_fixed_and_uses_its_own_key(self):
        from jevkit.providers import resolve_provider

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {
                "JEV_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "synthetic-openrouter-key",
                "TYPESAFE_API_KEY": "synthetic-typesafe-key",
            },
            clear=True,
        ):
            profile = resolve_provider(config_root=Path(tmp))
            self.assertEqual(profile.provider_id, "openrouter")
            self.assertEqual(profile.endpoint, "https://openrouter.ai/api/alpha/decisions")
            self.assertEqual(profile.model, "typesafe/jev-1.13")
            self.assertEqual(profile.env_var, "OPENROUTER_API_KEY")

    def test_typesafe_profile_is_fixed_and_uses_its_own_key(self):
        from jevkit.providers import resolve_provider

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"JEV_PROVIDER": "typesafe", "TYPESAFE_API_KEY": "synthetic-typesafe-key"},
            clear=True,
        ):
            profile = resolve_provider(config_root=Path(tmp))
            self.assertEqual(profile.provider_id, "typesafe")
            self.assertEqual(profile.endpoint, "https://api.typesafe.ai/v1/systemone")
            self.assertEqual(profile.model, "jev-1.13.0")
            self.assertEqual(profile.env_var, "TYPESAFE_API_KEY")

    def test_provider_is_not_inferred_when_both_keys_exist(self):
        from jevkit.providers import resolve_provider

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "synthetic-openrouter-key",
                "TYPESAFE_API_KEY": "synthetic-typesafe-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(SafeError, "PROVIDER_SELECTION_REQUIRED"):
                resolve_provider(config_root=Path(tmp))

    def test_store_provider_credential_writes_owner_only_files(self):
        from jevkit.providers import resolve_provider, store_provider_credential

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            root = Path(tmp).resolve() / "config"
            store_provider_credential(
                "openrouter", "synthetic-openrouter-key", config_root=root
            )
            profile = resolve_provider(config_root=root)
            self.assertEqual(profile.provider_id, "openrouter")
            key_path = root / "openrouter-api-key"
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(key_path.stat().st_mode), 0o600)
            self.assertNotIn("synthetic-openrouter-key", (root / "provider").read_text())

    def test_owner_only_private_env_is_supported_outside_repository(self):
        from jevkit.providers import get_provider_credential, resolve_provider

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            root = Path(tmp).resolve() / "config"
            root.mkdir(mode=0o700)
            env_file = root / ".env"
            env_file.write_text(
                "JEV_PROVIDER=openrouter\n"
                "OPENROUTER_API_KEY=synthetic-openrouter-key\n"
                "TYPESAFE_API_KEY=\n"
            )
            env_file.chmod(0o600)
            profile = resolve_provider(config_root=root)
            self.assertEqual(profile.provider_id, "openrouter")
            self.assertEqual(
                get_provider_credential(profile, config_root=root),
                "synthetic-openrouter-key",
            )


class ProviderTransportTests(unittest.TestCase):
    def _case(self):
        item = fixture("01-skill-routing")
        questions = questions_for(spec(item["case_id"]), item["state"])
        return item, questions

    def _response(self, model: str, questions: dict) -> bytes:
        raw = simulated_response(questions, self._case()[0]["mock_values"])
        raw["model"] = model
        return json.dumps(raw).encode()

    def test_openrouter_uses_decisions_endpoint_model_and_bearer_key(self):
        from jevkit.client import evaluate
        from jevkit.providers import provider_profile

        item, questions = self._case()
        captured = {}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data)
            captured["timeout"] = timeout
            return Response(self._response("typesafe/jev-1.13", questions))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "synthetic-openrouter-key"},
            clear=True,
        ):
            root = Path(tmp)
            profile = provider_profile("openrouter")
            CallBudget(
                root,
                provider_id=profile.provider_id,
                provider_profile_sha256=profile.profile_sha256,
            ).grant(1, 1)
            result = evaluate(
                root,
                item["state"],
                questions,
                False,
                provider=profile,
                transport=transport,
            )
        self.assertEqual(captured["url"], "https://openrouter.ai/api/alpha/decisions")
        self.assertEqual(captured["authorization"], "Bearer synthetic-openrouter-key")
        self.assertEqual(captured["body"]["model"], "typesafe/jev-1.13")
        self.assertEqual(result["_provider_id"], "openrouter")

    def test_typesafe_direct_wire_contract_is_preserved(self):
        from jevkit.client import evaluate
        from jevkit.providers import provider_profile

        item, questions = self._case()
        captured = {}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data)
            return Response(self._response("jev-1.13.0", questions))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"TYPESAFE_API_KEY": "synthetic-typesafe-key"},
            clear=True,
        ):
            root = Path(tmp)
            profile = provider_profile("typesafe")
            CallBudget(
                root,
                provider_id=profile.provider_id,
                provider_profile_sha256=profile.profile_sha256,
            ).grant(1, 1)
            result = evaluate(
                root,
                item["state"],
                questions,
                False,
                provider=profile,
                transport=transport,
            )
        self.assertEqual(captured["url"], "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(captured["authorization"], "Bearer synthetic-typesafe-key")
        self.assertEqual(captured["body"]["model"], "jev-1.13.0")
        self.assertEqual(result["_provider_id"], "typesafe")


class GlobalHybridPluginTests(unittest.TestCase):
    def test_global_hybrid_exposes_live_tool_but_requires_workspace(self):
        from jevkit import mcp_server
        from jevkit.runtime import GLOBAL_HYBRID, RuntimeContext

        with tempfile.TemporaryDirectory() as tmp:
            context = RuntimeContext(ROOT, Path(tmp) / "state", GLOBAL_HYBRID)
            definitions = {tool["name"]: tool for tool in mcp_server.tools(ctx=context)}
            self.assertIn("jev_evaluate", definitions)
            schema = definitions["jev_evaluate"]["inputSchema"]
            self.assertIn("workspace_path", schema["required"])

    def test_global_hybrid_cannot_evaluate_without_human_workspace_grant(self):
        from jevkit.runtime import GLOBAL_HYBRID, RuntimeContext

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"JEV_PROVIDER": "typesafe", "TYPESAFE_API_KEY": "synthetic-typesafe-key"},
            clear=True,
        ):
            root = Path(tmp)
            workspace = root / "repo"
            init_repo(workspace)
            context = RuntimeContext(ROOT, root / "state", GLOBAL_HYBRID)
            with self.assertRaisesRegex(SafeError, "LIVE_NOT_AUTHORIZED"):
                context.evaluate(
                    "01-skill-routing", workspace_root=workspace
                )

    def test_switching_provider_invalidates_existing_workspace_grant(self):
        from jevkit.runtime import PROJECT_LIVE, RuntimeContext

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "repo"
            init_repo(workspace)
            with patch.dict(
                os.environ,
                {"JEV_PROVIDER": "typesafe", "TYPESAFE_API_KEY": "synthetic-typesafe-key"},
                clear=True,
            ):
                direct = RuntimeContext(ROOT, root / "state", PROJECT_LIVE, workspace)
                direct.create_live_grant(calls=2, minutes=5)
                self.assertTrue(direct.read_live_grant()["enabled"])
            with patch.dict(
                os.environ,
                {"JEV_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "synthetic-openrouter-key"},
                clear=True,
            ):
                routed = RuntimeContext(ROOT, root / "state", PROJECT_LIVE, workspace)
                self.assertFalse(routed.read_live_grant()["enabled"])


if __name__ == "__main__":
    unittest.main()
