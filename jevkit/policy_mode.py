"""Local, deterministic control plane for selective Jev use in Codex."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .security import private_dir, private_json, screen


POLICY_MODES = ("off", "assist", "enforce")
DEFAULT_POLICY_MODE = "assist"
GOVERNED_TOOLS = ("Bash", "apply_patch", "Edit", "Write")
_SENSITIVE = frozenset(
    {
        "API_KEY",
        "BEARER_TOKEN",
        "CREDENTIAL",
        "CREDENTIAL_ASSIGNMENT",
        "CREDENTIAL_URL",
        "JWT",
        "PRIVATE_KEY",
    }
)
_ROUTES = (
    ("06-injection-triage", (r"prompt injection", r"suspicious instruction", r"untrusted instruction")),
    ("07-claim-verification", (r"verify (?:this )?claim", r"fact[- ]?check", r"claim against")),
    ("08-completion-gate", (r"completion gate", r"acceptance evidence", r"is (?:this|the work) complete")),
    ("09-patch-review", (r"review (?:this )?patch", r"patch risk", r"diff risk")),
    ("10-semantic-lint", (r"semantic lint", r"meaning[- ]level contradiction", r"contradiction")),
    ("11-failure-classification", (r"classify (?:this )?failure", r"failure category", r"root cause route")),
    ("13-issue-triage", (r"triage (?:this )?issue", r"issue priority", r"issue severity")),
    ("14-incident-triage", (r"triage (?:this )?incident", r"incident priority", r"incident severity")),
    ("15-test-selection", (r"select (?:the )?(?:right )?tests?", r"which tests?", r"test set")),
    ("16-documentation-drift", (r"documentation drift", r"docs? (?:still )?match", r"stale documentation")),
    ("17-security-review-routing", (r"security review route", r"route (?:this )?security", r"security finding")),
    ("18-support-triage", (r"support triage", r"route (?:this )?support", r"support request")),
    ("19-research-ranking", (r"rank (?:these )?sources?", r"best sources?", r"research ranking")),
    ("20-memory-admission", (r"save (?:this )?(?:to )?memory", r"memory admission", r"remember (?:this|that)")),
    ("04-file-ranking", (r"rank (?:these )?(?:candidate )?files?", r"relevant files?", r"which files?")),
    ("05-context-sieve", (r"context sieve", r"select (?:the )?context", r"keep relevant context")),
    ("01-skill-routing", (r"choose (?:the )?(?:best|right|smallest) skill", r"skill routing", r"which skill")),
    ("02-task-routing", (r"route (?:this )?task", r"task routing", r"which workflow")),
    ("03-tool-selection", (r"choose (?:the )?(?:best|right) tool", r"tool selection", r"which tool")),
    ("12-worker-routing", (r"choose (?:the )?(?:best|right) (?:worker|agent)", r"worker routing", r"which agent")),
)


def _config_root() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    return (
        Path(configured).expanduser() / "qualixar-jev-control"
        if configured
        else Path.home() / ".config" / "qualixar-jev-control"
    )


def policy_mode(config_root: Path | None = None) -> str:
    override = os.environ.get("QUALIXAR_JEV_POLICY_MODE")
    if override is not None:
        candidate = override.strip().lower()
        return candidate if candidate in POLICY_MODES else DEFAULT_POLICY_MODE
    path = (config_root or _config_root()) / "policy-mode"
    try:
        candidate = path.read_text().strip().lower()
    except (OSError, UnicodeError):
        return DEFAULT_POLICY_MODE
    return candidate if candidate in POLICY_MODES else DEFAULT_POLICY_MODE


def write_policy_mode(mode: str, config_root: Path | None = None, *, overwrite: bool = True) -> Path:
    candidate = mode.strip().lower()
    if candidate not in POLICY_MODES:
        raise ValueError("INVALID_POLICY_MODE")
    root = config_root or _config_root()
    private_dir(root)
    path = root / "policy-mode"
    if path.is_symlink():
        raise ValueError("UNSAFE_POLICY_PATH")
    if path.exists() and not overwrite:
        return path
    descriptor, temporary_name = tempfile.mkstemp(prefix="policy-mode.tmp-", dir=root)
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            descriptor = -1
            stream.write(candidate + "\n")
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return path


def classify_intent(intent: str, *, mode: str | None = None) -> dict[str, Any]:
    selected_mode = (mode or policy_mode()).strip().lower()
    if selected_mode not in POLICY_MODES:
        selected_mode = DEFAULT_POLICY_MODE
    if not isinstance(intent, str) or not intent.strip():
        return {"status": "SKIP", "case_id": None, "reason_code": "EMPTY_INTENT"}
    _cleaned, findings = screen(intent)
    if _SENSITIVE.intersection(findings):
        return {"status": "BLOCK", "case_id": None, "reason_code": "SENSITIVE_INPUT"}
    if selected_mode == "off":
        return {"status": "SKIP", "case_id": None, "reason_code": "POLICY_OFF"}
    normalized = " ".join(intent.lower().split())
    for case_id, patterns in _ROUTES:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return {
                "status": "REQUIRE" if selected_mode == "enforce" else "SUGGEST",
                "case_id": case_id,
                "reason_code": "BOUNDED_SEMANTIC_DECISION",
            }
    return {"status": "SKIP", "case_id": None, "reason_code": "DETERMINISTIC_OR_UNMATCHED"}


def policy_status(config_root: Path | None = None) -> dict[str, Any]:
    return {
        "version": "1.1.1",
        "mode": policy_mode(config_root),
        "default_mode": DEFAULT_POLICY_MODE,
        "modes": list(POLICY_MODES),
        "local_classifier": True,
        "classifier_external_calls": 0,
        "prompt_text_persisted": False,
        "governed_tools": list(GOVERNED_TOOLS),
        "execution_authorized": False,
    }


def _ledger_path(data_root: Path, turn_id: str) -> Path:
    digest = hashlib.sha256(turn_id.encode("utf-8")).hexdigest()
    return data_root / "policy" / f"{digest}.json"


def _read_ledger(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
            return None
        value = json.loads(path.read_text())
    except (OSError, ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _valid_live_response(response: Any, case_id: str) -> bool:
    if not isinstance(response, dict) or response.get("isError") is not False:
        return False
    content = response.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        return False
    text = content[0].get("text")
    if not isinstance(text, str) or len(text) > 512_000:
        return False
    try:
        receipt = json.loads(text)
    except (ValueError, RecursionError):
        return False
    policy = receipt.get("policy") if isinstance(receipt, dict) else None
    record_hash = receipt.get("record_sha256") if isinstance(receipt, dict) else None
    return bool(
        receipt.get("mode") == "live"
        and receipt.get("case_id") == case_id
        and isinstance(policy, dict)
        and policy.get("execution_authorized") is False
        and isinstance(record_hash, str)
        and re.fullmatch(r"[0-9a-f]{64}", record_hash)
    )


def _is_qualixar_jev_evaluate(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return (
        lowered.startswith("mcp__")
        and "qualixar" in lowered
        and lowered.endswith("jev_evaluate")
    )


def handle_hook_event(event: dict[str, Any], *, data_root: Path, mode: str | None = None) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        return None
    event_name = event.get("hook_event_name")
    turn_id = event.get("turn_id")
    if not isinstance(turn_id, str) or not turn_id or len(turn_id) > 256:
        return None
    selected_mode = mode or policy_mode()
    ledger_path = _ledger_path(data_root, turn_id)

    if event_name == "UserPromptSubmit":
        prompt = event.get("prompt")
        if not isinstance(prompt, str) or len(prompt.encode("utf-8")) > 64_000:
            return None
        decision = classify_intent(prompt, mode=selected_mode)
        status = decision["status"]
        if status == "SKIP":
            return None
        if status == "BLOCK":
            context = (
                "Jev Policy Mode: BLOCK. Sensitive material was detected locally; do not send "
                "this state to Jev. Derive a reviewed synthetic or public representation first."
            )
        else:
            case_id = decision["case_id"]
            context = (
                f"Jev Policy Mode: {status} case={case_id}. Use jev_describe, minimize and classify "
                "the state, then use jev_evaluate only with a valid workspace grant. Jev advice "
                "never authorizes execution."
            )
        if status == "REQUIRE":
            ledger = {
                "schema_version": 1,
                "turn_sha256": hashlib.sha256(turn_id.encode()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "workspace_sha256": hashlib.sha256(str(event.get("cwd", "")).encode()).hexdigest(),
                "case_id": decision["case_id"],
                "status": "pending",
                "reason_code": decision["reason_code"],
            }
            private_json(ledger_path, ledger)
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }

    ledger = _read_ledger(ledger_path)
    if not ledger or ledger.get("status") != "pending":
        return None
    tool_name = event.get("tool_name")
    if not isinstance(tool_name, str):
        return None

    if event_name == "PostToolUse" and _is_qualixar_jev_evaluate(tool_name):
        supplied_case = (event.get("tool_input") or {}).get("case_id") if isinstance(event.get("tool_input"), dict) else None
        if supplied_case == ledger.get("case_id") and _valid_live_response(
            event.get("tool_response"), ledger.get("case_id")
        ):
            ledger["status"] = "satisfied"
            private_json(ledger_path, ledger)
        return None

    if event_name == "PreToolUse" and tool_name in GOVERNED_TOOLS:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Jev Policy Mode requires {ledger.get('case_id')} before this governed tool. "
                    "Call jev_describe and jev_evaluate with minimized approved state, or switch "
                    "Policy Mode to assist/off in a private terminal."
                ),
            }
        }
    return None
