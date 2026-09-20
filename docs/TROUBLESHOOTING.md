# Troubleshooting: fail precisely, do not rewrite the stack

| Symptom | Safe diagnosis and next action |
|---|---|
| Python older than 3.11 | Install a supported Python through an approved existing manager; do not alter system Python. |
| Core tests fail | Preserve output, locate one failure, repair only the relevant module and rerun. No live calls. |
| MCP missing | Confirm opened project root, normal trust status, generated project config and session restart. |
| CLI works but Codex tool missing | Host integration is unverified; inspect actual host MCP status, not only the CLI result. |
| Existing `jev_control` entry | Installer refuses to overwrite it. Review registration ownership and avoid a duplicate server. |
| Package moved after setup | Managed absolute paths differ; use rollback at original location or reviewed manual repair, not global overwrite. |
| Official skill missing | Verify discovery scope, reuse existing installation, inspect official source before approved install. |
| NO_CREDENTIAL | Use private helper or approved environment injection. Never print the key or dump the environment. |
| LIVE_NOT_AUTHORIZED / exhausted grant | Human deliberately approves another bounded grant; no automatic renewal. |
| Custom state rejected | Requires `--allow-custom` human grant and prior content review. Fixture mode never evaluates custom data. |
| Sensitive-data false positive | Inspect the local synthetic input privately and narrow the data; never disable all screening. |
| 401 | Human checks/revokes/replaces key privately. Do not retry in a loop or show raw provider body. |
| 422 / contract mismatch | Stop live use; compare official API with the adapter and create a fixture-driven regression test. |
| 429 / 529 | Bounded retry consumes attempts. Stop when grant is exhausted; no infinite backoff. |
| Timeout | May have been processed remotely. Do not automatically repeat; reconcile privately. |
| Network/proxy policy blocks | Request approved connectivity. Never disable TLS or bypass managed restrictions. |
| Viewer has no live receipt | Run actual live cases first; never relabel fixtures. Refresh reads files, not the API. |
| Viewer excludes custom run | Intentional privacy boundary. Keep custom results private or use separately reviewed media. |
| Capture browser missing | Use optional approved dependency helper, then test one workflow. |
| Browser local navigation blocked | Respect policy; an offline local-data snapshot is supported and explicitly labeled. |
| ffmpeg missing | Use an approved installation; WebM remains valid source footage without MP4 conversion. |
| Live answer differs from fixture | Preserve it as a semantic finding. A fixture is not an empirical gold label. |

Two focused repair attempts maximum for unexplained host/API failure. Report the safe
error code and completed stages; do not keep spending or replace the whole system.
