# Qualixar Jev Codex Workbench 1.1.3

The installed facade adds standing workspace operation, compact results and local recovery
while retaining the original `jevkit` compatibility path. Optional MLX is isolated; the browser
bridge uses the existing authorized Computer Use tab. SLM and native host permissions stay intact.

Enroll privately once with `python3 auto_entry.py enroll --workspace <path> --provider existing`.
See `python3 auto_entry.py --help` for local routes, status, warmup, probe, statistics and revoke.
Known browser origins are supplied at enrollment with repeated `--browser-origin` arguments.
Native hook review is still required after the plugin is refreshed from this actual source.

The service shares budgets/cache by workspace, not by code revision. Changed evidence triggers
fresh evaluation. Full receipts stay local; compact MCP responses contain a receipt ID for
`jev_recall`. A failure to optimize preserves ordinary Codex behavior and original evidence.

Automatic prompt preparation uses a local shortlist unless `prepare` is explicitly routed
to local Laya-MLX. Automatic `PostToolUse` reduction runs only with a local Laya-MLX
`sieve` route. Explicit remote Jev calls still transmit their supplied state, so the
operator must review it; the enrollment classification label cannot detect ordinary
confidential prose. The browser bridge and broker both check the owner's step limit.

The original strict grant workflow in `docs/LIVE_VALIDATION.md` applies only to
unenrolled legacy operation. Enrolled workbench calls do not need terminal
per-request grants, while native Codex tool permissions remain in force.
Use your existing private credential. Do not paste keys into Codex or the browser REPL.

For MLX: run `python3 scripts/install_laya_mlx.py`, then `auto_entry.py route-local` for the
specific recipe(s), warmup and probe. First installation is an owner-approved model download,
not training. Keep large-context browser judgments on Jev unless independently evaluated.

Validation commands:
```
python3 -m unittest discover -s tests -v
node --test tests/jev_auto_browser.test.mjs
python3 jev.py suite
python3 scripts/verify_package.py
```

Offline tests alone do not establish native browser compatibility, MLX speed or cost savings.
See [architecture](ARCHITECTURE_1_1_3.md) for the native flow and trust boundaries.
The delivered package's native acceptance matrix and measurement contract remain release gates.
Local character-withholding counters are proposals, not native token/invoice measurements.
