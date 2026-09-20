# Rollback and removal

Revoke outstanding live calls first, then roll back the project MCP configuration:

```bash
.venv/bin/python scripts/enable_live.py --workspace "$PWD" --revoke
.venv/bin/python scripts/rollback.py
```

Rollback only restores the saved project config when hashes show the current managed
file and original backup have not changed unexpectedly. Otherwise it stops for manual
review. It does not overwrite newer edits, touch global config, change models, revoke
the provider API key, or delete evidence.

To fully remove this isolated project, close its Codex session, stop the viewer, archive
reviewed evidence, and delete the project folder using the OS file manager. The optional
external credential file remains; the human may delete it privately and revoke the
provider key through TypeSafe's account interface. Never ask the agent to display it.
The official TypeSafe skill is not owned by this kit and should not be removed as a
side effect. Optional Playwright browser caches may be shared; do not delete them blindly.
