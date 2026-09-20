"""Contracts for the Codex hook-backed Jev Policy Mode."""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from jevkit.engine import ROOT


PLUGIN = ROOT / "plugins" / "qualixar-jev-control"
HOOK = PLUGIN / "hooks" / "jev_policy_hook.py"


def run_hook(event: dict, *, mode: str = "assist", data_root: Path) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment.update(
        {
            "PLUGIN_ROOT": str(PLUGIN),
            "PLUGIN_DATA": str(data_root),
            "QUALIXAR_JEV_POLICY_MODE": mode,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
    )


class PolicyModeTests(unittest.TestCase):
    def test_local_classifier_skips_deterministic_work_and_routes_semantic_work(self):
        from jevkit.policy_mode import classify_intent

        skipped = classify_intent("Read README.md and show line 10.", mode="enforce")
        routed = classify_intent(
            "Rank these candidate files before we load their full contents.", mode="assist"
        )
        required = classify_intent(
            "Rank these candidate files before we load their full contents.", mode="enforce"
        )
        self.assertEqual(skipped["status"], "SKIP")
        self.assertEqual(routed["status"], "SUGGEST")
        self.assertEqual(routed["case_id"], "04-file-ranking")
        self.assertEqual(required["status"], "REQUIRE")

    def test_local_classifier_blocks_detected_secret_material(self):
        from jevkit.policy_mode import classify_intent

        decision = classify_intent(
            "Evaluate this credential: sk-proj-abcdefghijklmnop123456", mode="assist"
        )
        self.assertEqual(decision["status"], "BLOCK")
        self.assertEqual(decision["reason_code"], "SENSITIVE_INPUT")
        self.assertNotIn("sk-proj", json.dumps(decision))

    def test_assist_hook_adds_compact_context_without_persisting_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = "Choose the best skill for this documentation task."
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-assist",
                    "prompt": prompt,
                    "cwd": "/synthetic/workspace",
                },
                mode="assist",
                data_root=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Jev Policy Mode: SUGGEST", context)
            self.assertLess(len(context), 700)
            self.assertEqual(list(root.rglob("*.json")), [])
            self.assertNotIn(prompt, result.stdout)

    def test_enforce_hook_blocks_governed_tool_until_successful_jev_evaluation(self):
        from jevkit.runtime import workspace_binding

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binding = workspace_binding(ROOT)
            request_id = "policy-" + hashlib.sha256(b"turn-enforce").hexdigest()[:24]
            submitted = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-enforce",
                    "prompt": "Rank the most relevant files before reading them all.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)

            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-enforce",
                    "tool_name": "Bash",
                    "tool_input": {"command": "rg --files"},
                },
                mode="enforce",
                data_root=root,
            )
            blocked_output = json.loads(blocked.stdout)
            self.assertEqual(
                blocked_output["hookSpecificOutput"]["permissionDecision"], "deny"
            )
            self.assertNotIn("rg --files", blocked.stdout)

            evaluated = run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": "turn-enforce",
                    "tool_name": "mcp__qualixar_jev__jev_evaluate",
                    "tool_input": {
                        "case_id": "04-file-ranking",
                        "workspace_path": binding["workspace_path"],
                        "request_id": request_id,
                        "data_classification": "internal-minimized",
                        "state": {"requirement": "synthetic", "patch": "synthetic"},
                    },
                    "tool_response": {
                        "isError": False,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "mode": "live",
                                        "variant": "custom",
                                        "case_id": "04-file-ranking",
                                        "data_classification": "internal-minimized",
                                        "request_id": request_id,
                                        "request_sha256": "b" * 64,
                                        "record_sha256": "a" * 64,
                                        "workspace_id": binding["workspace_id"],
                                        "revision": binding["revision"],
                                        "policy": {"execution_authorized": False},
                                    }
                                ),
                            }
                        ],
                    },
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr)

            allowed = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-enforce",
                    "tool_name": "Bash",
                    "tool_input": {"command": "rg --files"},
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(allowed.stdout, "")

            ledgers = list(root.rglob("*.json"))
            self.assertEqual(len(ledgers), 1)
            ledger_text = ledgers[0].read_text()
            self.assertNotIn("Rank the most relevant", ledger_text)
            self.assertNotIn("prompt_sha256", ledger_text)
            self.assertEqual(ledgers[0].stat().st_mode & 0o777, 0o600)

    def test_failed_jev_evaluation_does_not_satisfy_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-failed",
                    "prompt": "Select the right test set for this patch.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": "turn-failed",
                    "tool_name": "mcp__qualixar_jev__jev_evaluate",
                    "tool_response": {"isError": True},
                },
                mode="enforce",
                data_root=root,
            )
            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-failed",
                    "tool_name": "apply_patch",
                    "tool_input": {"command": "*** Begin Patch"},
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(
                json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )

    def test_unrelated_tool_named_jev_evaluate_cannot_satisfy_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-spoofed",
                    "prompt": "Rank these candidate files.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": "turn-spoofed",
                    "tool_name": "mcp__untrusted_qualixar_fake__jev_evaluate",
                    "tool_input": {"case_id": "04-file-ranking"},
                    "tool_response": {"isError": False, "content": []},
                },
                mode="enforce",
                data_root=root,
            )
            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-spoofed",
                    "tool_name": "Bash",
                    "tool_input": {"command": "true"},
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(
                json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )

    def test_non_object_receipt_cannot_satisfy_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-list-receipt",
                    "prompt": "Rank these candidate files.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root,
            )
            evaluated = run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": "turn-list-receipt",
                    "tool_name": "mcp__qualixar_jev__jev_evaluate",
                    "tool_input": {"case_id": "04-file-ranking"},
                    "tool_response": {
                        "isError": False,
                        "content": [{"type": "text", "text": "[]"}],
                    },
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-list-receipt",
                    "tool_name": "Bash",
                    "tool_input": {"command": "true"},
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(
                json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )

    def test_synthetic_live_receipt_cannot_satisfy_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-synthetic",
                    "prompt": "Rank these candidate files.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root,
            )
            receipt = {
                "mode": "live",
                "variant": "nominal",
                "case_id": "04-file-ranking",
                "data_classification": "synthetic",
                "request_sha256": "b" * 64,
                "record_sha256": "a" * 64,
                "policy": {"execution_authorized": False},
            }
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": "turn-synthetic",
                    "tool_name": "mcp__qualixar_jev__jev_evaluate",
                    "tool_input": {"case_id": "04-file-ranking"},
                    "tool_response": {
                        "isError": False,
                        "content": [{"type": "text", "text": json.dumps(receipt)}],
                    },
                },
                mode="enforce",
                data_root=root,
            )
            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": "turn-synthetic",
                    "tool_name": "Bash",
                    "tool_input": {"command": "true"},
                },
                mode="enforce",
                data_root=root,
            )
            self.assertEqual(
                json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )

    def test_enforce_blocks_oversized_prompt_and_private_ledger_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oversized = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-large",
                    "prompt": "x" * 64_001,
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root / "data",
            )
            self.assertEqual(json.loads(oversized.stdout)["decision"], "block")

            target = root / "target"
            target.mkdir()
            linked = root / "linked"
            linked.symlink_to(target, target_is_directory=True)
            unsafe = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-unsafe-ledger",
                    "prompt": "Rank these candidate files.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=linked,
            )
            self.assertEqual(json.loads(unsafe.stdout)["decision"], "block")

    def test_receipt_from_another_workspace_cannot_satisfy_enforcement(self):
        from jevkit.runtime import workspace_binding

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other = root / "other"
            other.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=other, check=True)
            subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=other, check=True)
            subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=other, check=True)
            (other / "baseline.txt").write_text("baseline\n")
            subprocess.run(["git", "add", "baseline.txt"], cwd=other, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=other, check=True)
            other_binding = workspace_binding(other)
            turn_id = "turn-cross-workspace"
            request_id = "policy-" + hashlib.sha256(turn_id.encode()).hexdigest()[:24]
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": turn_id,
                    "prompt": "Rank these candidate files.",
                    "cwd": str(ROOT),
                },
                mode="enforce",
                data_root=root / "data",
            )
            receipt = {
                "mode": "live",
                "variant": "custom",
                "case_id": "04-file-ranking",
                "data_classification": "internal-minimized",
                "request_id": request_id,
                "request_sha256": "b" * 64,
                "record_sha256": "a" * 64,
                "workspace_id": other_binding["workspace_id"],
                "revision": other_binding["revision"],
                "policy": {"execution_authorized": False},
            }
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "turn_id": turn_id,
                    "tool_name": "mcp__qualixar_jev__jev_evaluate",
                    "tool_input": {
                        "case_id": "04-file-ranking",
                        "workspace_path": other_binding["workspace_path"],
                        "request_id": request_id,
                        "data_classification": "internal-minimized",
                    },
                    "tool_response": {
                        "isError": False,
                        "content": [{"type": "text", "text": json.dumps(receipt)}],
                    },
                },
                mode="enforce",
                data_root=root / "data",
            )
            blocked = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "turn_id": turn_id,
                    "tool_name": "Bash",
                    "tool_input": {"command": "true"},
                },
                mode="enforce",
                data_root=root / "data",
            )
            self.assertEqual(
                json.loads(blocked.stdout)["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )

    def test_plugin_packages_reviewable_sync_hooks(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
        self.assertIn("UserPromptSubmit", hooks["hooks"])
        self.assertIn("PreToolUse", hooks["hooks"])
        self.assertIn("PostToolUse", hooks["hooks"])
        for groups in hooks["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertFalse(hook.get("async", False))
                    self.assertIn("${PLUGIN_ROOT}", hook["command"])


if __name__ == "__main__":
    unittest.main()
