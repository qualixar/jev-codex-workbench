# Contributing

Thank you for improving Qualixar Jev Control. Contributions should preserve the
central boundary: global installation may expose live Jev, but its provider is fixed
by private user configuration and its authority is explicit, expiring,
workspace-bound, revision-bound, and human-created.

## Development setup

```bash
python3 scripts/verify_package.py
python3 scripts/bootstrap.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python jev.py suite
```

Use synthetic data in tests and issues. Never commit keys, local grants, private
receipts, customer information, screenshots containing account data, or generated
`.codex/config.toml` files.

## Pull requests

Keep changes focused. Add or update tests for behavior changes. State which security
boundary is affected, what you ran, and what remains unverified. If a change modifies
the plugin runtime, regenerate it with `python3 scripts/package_plugin_runtime.py` and
prove that live invocation fails without the correct provider-bound workspace grant.

Before submitting:

```bash
python3 scripts/package_plugin_runtime.py
python3 scripts/generate_manifest.py
python3 scripts/verify_package.py
.venv/bin/python -m unittest discover -s tests -v
```

Do not weaken a failing gate, silently relabel fixture output as live evidence, or add
automatic credential/grant creation to make a demonstration easier.

By contributing, you agree that your contribution is licensed under the MIT License.
