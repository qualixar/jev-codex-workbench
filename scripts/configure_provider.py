#!/usr/bin/env python3
"""Human-only provider selection and hidden credential storage."""
from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevkit.providers import ProviderProfile, store_provider_credential
from jevkit.security import SafeError


def configure(
    *,
    config_root: Path | None = None,
    input_func: Callable[[str], str] = input,
    getpass_func: Callable[[str], str] = getpass.getpass,
    output_func: Callable[[str], None] = print,
) -> ProviderProfile:
    output_func("Choose the service that will process live Jev requests:")
    output_func("  1. OpenRouter Decisions (recommended for most users)")
    output_func("  2. TypeSafe direct")
    choice = input_func("Provider [1/2]: ").strip()
    providers = {"1": "openrouter", "2": "typesafe"}
    if choice not in providers:
        raise SafeError("INVALID_PROVIDER_SELECTION")
    provider_id = providers[choice]
    key = getpass_func(f"{provider_id} API key (hidden): ").strip()
    profile = store_provider_credential(provider_id, key, config_root=config_root)
    output_func(
        f"Configured {profile.display_name}. The key was not printed and is stored "
        "in an owner-only local file outside the repository."
    )
    return profile


def main() -> int:
    if not sys.stdin.isatty():
        raise SafeError("PRIVATE_TERMINAL_REQUIRED: run this yourself outside agent logs")
    configure()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SafeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
