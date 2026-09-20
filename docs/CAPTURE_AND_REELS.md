# Evidence capture and reel-source workflow

## Different media prove different things

1. A **native Codex recording** can show the actual host invoking the MCP tool and editing
   code. Record it manually using the operating system's screen-recording controls.
2. A **Workbench recording** shows an actual browser rendering of stored receipts. It
   does not show a new inference, native Codex, or live-streaming model activity.
3. An **architecture diagram** explains a design. It is not execution evidence.

Always keep FIXTURE / LIVE RECORDED RUN / OFFLINE SNAPSHOT labels visible. Never crop,
blur or cover those labels to improve a reel. Recording an actual live receipt later
is still a replay, not a real-time inference capture.

## Optional dependencies

The core installer is offline. Capture is a separate approved network step:

```bash
.venv/bin/python scripts/install_capture.py --approved-network-install
```

This installs the pinned Playwright requirement and Chromium for the project. Use
approved local package management for ffmpeg when absent. Do not install system packages
with sudo or bypass managed download restrictions. The build-environment capture used
a different already-installed Playwright version; see the validation report and verify
the pinned target on your Mac before marking the capture stage complete.

## Browser capture

First execute cases so their receipts exist. Then:

```bash
.venv/bin/python scripts/capture.py --case 08-completion-gate --variant adversarial --orientation both --seconds 8
.venv/bin/python scripts/capture.py --case all --mode live --variant nominal --orientation both --seconds 8
```

Outputs are under `artifacts/captures/<run-id>/<orientation>/`: an actual PNG, WebM,
and a manifest bound to the source run and file hashes. The script fails if no matching
run exists. No synthetic fallback. The `--offline-render` option renders the same local
HTML and stored JSON without browser network activity and labels it OFFLINE SNAPSHOT.
It does not bypass a blocked site or access data outside the package.

Portrait capture is 1080×1920; landscape is 1920×1080. The viewport is a selected
reading state, not a claim that every long receipt fits on screen. For detailed input
or output, take additional manual scroll shots while retaining context and labels.

## MP4 editorial source

```bash
.venv/bin/python scripts/make_reel.py --capture-dir artifacts/captures/RUN_ID/portrait
```

Replace RUN_ID with an actual recorded run ID. The helper verifies the source video
hash and creates a padded H.264 MP4 without cropping. No audio, generated claims,
automatic posting, or completed narration is added. These are **reel-source clips**
for your later editor, not finished social videos.

## A useful 30-second evidence sequence

0–5s: state the engineering problem with the real input visible.
5–12s: native Codex asks the bounded question, or label a stored-receipt replay.
12–20s: show the typed answer and the separate policy outcome.
20–26s: show the counterexample or uncertain case; do not hide failure modes.
26–30s: state the limitation and actual next action.

Use the case-specific notes in `docs/use_cases/`. Keep API-key entry off camera.
Before native recording, disable notification previews, hide account/usage panels,
use the synthetic demo folder, and close unrelated tabs. No automatic OS permission
requests or hidden recording occurs in this package.

## Static share-back and export

```bash
.venv/bin/python scripts/export_viewer.py
.venv/bin/python scripts/export_evidence.py --include-captures
```

The HTML is a network-free snapshot. The ZIP contains screened synthetic receipts,
matching captures, hashes and a claim ledger. It excludes custom-source data,
credentials, .local, Codex configuration and native recordings. Review every frame
before sharing. Optional reviewed native footage must be supplied separately.
