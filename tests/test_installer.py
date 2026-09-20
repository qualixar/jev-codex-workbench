"""Public installer tests. No real key, home config, or plugin state is touched."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jevkit.engine import ROOT


def load_script(name: str):
    path = ROOT / "scripts" / name
    specification = importlib.util.spec_from_file_location("jev_" + name, path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class ProviderSetupTests(unittest.TestCase):
    def test_hidden_setup_selects_openrouter_without_echoing_key(self):
        setup = load_script("configure_provider.py")
        messages = []
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            result = setup.configure(
                config_root=Path(tmp).resolve() / "config",
                input_func=lambda _prompt: "1",
                getpass_func=lambda _prompt: "synthetic-openrouter-key",
                output_func=messages.append,
            )
            self.assertEqual(result.provider_id, "openrouter")
            self.assertNotIn("synthetic-openrouter-key", "\n".join(messages))

    def test_hidden_setup_selects_typesafe_without_echoing_key(self):
        setup = load_script("configure_provider.py")
        messages = []
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            result = setup.configure(
                config_root=Path(tmp).resolve() / "config",
                input_func=lambda _prompt: "2",
                getpass_func=lambda _prompt: "synthetic-typesafe-key",
                output_func=messages.append,
            )
            self.assertEqual(result.provider_id, "typesafe")
            self.assertNotIn("synthetic-typesafe-key", "\n".join(messages))

    def test_env_example_has_placeholders_only(self):
        text = (ROOT / ".env.example").read_text()
        self.assertIn("JEV_PROVIDER=openrouter", text)
        self.assertIn("OPENROUTER_API_KEY=", text)
        self.assertIn("TYPESAFE_API_KEY=", text)
        self.assertNotRegex(text, r"(?:sk-or-|ts_[A-Za-z0-9])")


class InstallerTests(unittest.TestCase):
    def test_policy_mode_defaults_to_assist_without_overwriting_user_choice(self):
        from jevkit.policy_mode import policy_mode, write_policy_mode

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            installer = load_script("install.py")
            installer.ensure_default_policy(root)
            self.assertEqual(policy_mode(root), "assist")
            write_policy_mode("enforce", root)
            installer.ensure_default_policy(root)
            self.assertEqual(policy_mode(root), "enforce")

    def test_installer_uses_native_codex_marketplace_and_plugin_commands(self):
        installer = load_script("install.py")
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)

            class Result:
                returncode = 0
                stdout = "{}"
                stderr = ""

            return Result()

        installer.install_plugin(ROOT, runner=runner)
        self.assertEqual(
            commands,
            [
                ["codex", "plugin", "marketplace", "add", str(ROOT), "--json"],
                [
                    "codex",
                    "plugin",
                    "add",
                    "qualixar-jev-control@qualixar-jev",
                    "--json",
                ],
            ],
        )


if __name__ == "__main__":
    unittest.main()
