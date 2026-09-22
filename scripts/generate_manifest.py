#!/usr/bin/env python3
"""Generate the derived release manifest without overwriting baseline evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git", ".venv", ".local", ".codex", ".mypy_cache", ".ruff_cache",
    "artifacts", ".captures", "__pycache__",
}
EXCLUDED_NAMES = {"MANIFEST.json", ".DS_Store"}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and not path.is_symlink()
        and not (set(relative.parts) & EXCLUDED_PARTS)
        and path.name not in EXCLUDED_NAMES
        and path.suffix != ".pyc"
    )


def main() -> int:
    files = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if included(path)
    }
    manifest = {
        "version": "1.1.3",
        "hash_algorithm": "sha256",
        "note": (
            "Global-hybrid release manifest generated from the public source tree. "
            "Integrity hashes detect local changes; they are not a signed publisher attestation."
        ),
        "files": files,
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"Generated MANIFEST.json with {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
