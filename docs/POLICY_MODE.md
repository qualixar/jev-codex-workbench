# Jev Policy Mode for Codex

Policy Mode separates two jobs that should not be confused. A local deterministic
control plane decides whether a task resembles one of the 20 supplied bounded judgment
workflows. Jev is the optional decision plane for the matched semantic question. The
classifier makes no network request, reads no credential, and stores no prompt text.

The system is built to save Codex tokens. A narrow Jev decision can select the files,
tests, tools, skills, sources, or context worth deeper work before Codex pays to inspect
every candidate. That mechanism can reduce context and tool exploration while leaving
reasoning, code generation, execution, and final authority with Codex and the human operator.

## Modes

`off` disables policy routing. Policy Mode ships ON in `assist` by default and gives Codex a short instruction
when a workflow matches. `enforce` additionally records a per-turn pending decision and
uses a synchronous `PreToolUse` hook to deny Bash or file-edit calls until the matching
`jev_evaluate` call succeeds.

Enforcement is deliberately selective. Reading a named file, performing arithmetic,
running a deterministic check, or answering an unmatched question does not require Jev.
Sending every Codex turn to a remote model would increase latency, external data exposure,
and API usage without proving that the extra judgment was useful.

## Control flow

```text
User prompt
   |
   v
Local classifier -- sensitive material --> BLOCK external evaluation
   |
   +-- no bounded match --> SKIP
   |
   +-- match + assist --> SUGGEST matching workflow
   |
   `-- match + enforce --> REQUIRE matching workflow
                               |
                               v
                     workspace/revision grant
                               |
                               v
                         jev_evaluate
                               |
                               v
                     local deterministic policy
                               |
                               v
                governed Codex tool may proceed
```

The per-turn ledger contains the matched case, a generated request ID, the canonical Git
workspace identity and revision, a reason code, and the gate state. It does not contain
the prompt, a prompt fingerprint, tool command, credential, or Jev request body. Files are
stored under Codex's private plugin data directory with owner-only permissions.

## Trust and failure behavior

Codex requires the user to review new or modified plugin hooks. Until they are trusted,
Codex skips them. Use `/hooks` after installation or upgrade and inspect the exact three
hook definitions before approving them.

Assist mode never blocks work. Enforce mode blocks only the declared governed tools for
a matched turn. A failed, synthetic, or mismatched Jev evaluation does not satisfy the gate;
enforcement requires a request-bound custom evaluation classified as `public` or
`internal-minimized`. Switch to
`assist` or `off` from a private terminal if the provider or grant is unavailable; Policy
Mode never creates or expands a live grant itself.

## Token and cost claims

The architecture is designed to let a small bounded decision happen before Codex loads
more files or explores more tools. That is a design objective, not a measured saving.
TypeSafe reports tokens used by its own request, but those fields do not establish how
many Codex tokens were avoided. Publish a percentage only after a controlled Policy Mode
off/on benchmark captures Codex-side usage under the same tasks and acceptance criteria.
