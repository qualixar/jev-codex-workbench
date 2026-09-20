#!/usr/bin/env python3
"""Build the plugin's dual-provider, workspace-gated runtime from an allowlist."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "qualixar-jev-control"
TARGET = PLUGIN / "runtime"


def sources() -> list[Path]:
    files = [ROOT / "jev.py"]
    files.extend(
        source
        for source in sorted((ROOT / "jevkit").glob("*.py"))
    )
    files.extend(sorted((ROOT / "use_cases").glob("*.json")))
    files.extend(sorted((ROOT / "fixtures").glob("*/*.json")))
    return files


def relative_destination(source: Path) -> Path:
    if source == ROOT / "jev.py":
        return Path("jev.py")
    return source.relative_to(ROOT)


def main() -> int:
    if TARGET.parent != PLUGIN or TARGET.name != "runtime":
        raise RuntimeError("unsafe plugin runtime target")
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True, mode=0o755)
    hashes: dict[str, str] = {}
    for source in sources():
        destination = TARGET / relative_destination(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        hashes[str(destination.relative_to(TARGET))] = hashlib.sha256(
            destination.read_bytes()
        ).hexdigest()
    build_mode = TARGET / "jevkit" / "build_mode.py"
    build_mode.write_text(
        '"""Generated global-hybrid plugin capability gate."""\n\nOFFLINE_ONLY = False\n'
    )
    hashes[str(build_mode.relative_to(TARGET))] = hashlib.sha256(
        build_mode.read_bytes()
    ).hexdigest()
    manifest = {
        "adapter_version": "1.1.2-trust-ux",
        "mode": "global-hybrid",
        "live_evaluation_exposed": True,
        "credential_forwarding_configured": False,
        "files": hashes,
    }
    (TARGET / "RUNTIME_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"Packaged {len(hashes)} files into {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
