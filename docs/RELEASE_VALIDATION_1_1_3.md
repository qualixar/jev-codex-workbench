# Qualixar Jev Codex Workbench 1.1.3 validation

This note records the scope of the pre-release checks. It contains no private workspace content, credentials, browser cookies, or provider receipts. Results from one development Mac are functional evidence, not a general performance benchmark.

## Source and package

- The clean release checkout passed 300 Python tests, all supplied fixture contracts, 29 Node browser-bridge tests, and the 349-file release manifest check.
- The installed plugin's MCP handshake returned version 1.1.3 with 11 tools, including `jev_auto_status`, `jev_prepare`, `jev_reduce`, and `jev_recall`.
- Codex CLI listed the Qualixar `PreToolUse` and `PostToolUse` hooks as active and Trusted after the final local plugin refresh.
- The source and installed plugin cache matched for the hook, browser bridge, and changed runtime modules.

## Functional checks

- An enrolled workspace used its standing policy without a per-request Jev terminal grant. A synthetic live completion-gate input returned `REVIEW`; that is a valid cautious outcome, not an accuracy result. A repeated identical request was a cache hit, and two concurrent identical requests reserved one provider attempt.
- A child on the same workspace received the cached decision and reserved zero additional provider attempts.
- The installed explicit reduction tool withheld 1,878 characters from synthetic text, kept a required line, and exact recall restored an omitted line range. The installed hook script also kept a failing command and an instruction-file read unchanged in synthetic tests.
- The installed browser bridge reached the private broker from Codex's Computer Use runtime, reused one already authorized public documentation tab for bounded navigation, and verified each destination in that same tab. Both bridge and broker rejected steps beyond the enrolled cap.
- The optional pinned Laya-MLX worker passed runtime/checkpoint hash checks and returned actual local inference for three fresh-nonce synthetic probes on an already warm worker.
- The installed workbench runtime started in an isolated home with no SLM configuration and served offline health/catalog calls. On the development host, SLM remained enabled and healthy and the selected Codex coding model was unchanged.

## Measurement limit

The local MLX warm-worker probe durations were 0.225, 0.077, and 0.078 seconds for repeated versions of one synthetic billing classification. They are not cold-start numbers or an accuracy sample. The broker also records characters withheld and provider-call latency, but those counters are not Codex host tokens or task elapsed time.

A read-only Codex CLI baseline completed a small source lookup. The attempted Jev-assisted treatment could not call `jev_prepare` because that CLI run used a `never` approval policy. The treatment is invalid for a matched accepted-task comparison, so **no host-token, total-cost, subscription-quota, or task-time savings percentage is claimed**. The workbench is designed to reduce unnecessary context and repeated decisions; measured savings require accepted runs under the same host model and permission settings.

## Reproduce the offline gates

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 jev.py suite
node --test tests/jev_auto_browser.test.mjs
python3 scripts/verify_package.py
```

See [architecture](ARCHITECTURE_1_1_3.md), [security](../SECURITY.md), and [hook trust](TRUSTING_HOOKS.md) for the boundaries behind these checks.
