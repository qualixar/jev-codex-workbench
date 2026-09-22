# Security policy

## Supported release

Security fixes are applied to the latest tagged release. Version 1.1.3 supports
owner-approved standing enrollment for a reviewed workspace, with an expiry and
daily call/payload limits. Unenrolled legacy workspaces retain the older
request-bound grant path. Neither path grants Codex execution authority.

## Report a vulnerability

Do not open a public issue for a suspected vulnerability, exposed credential, or
sensitive receipt. Email **varun.pratap.bhardwaj@gmail.com** with:

- the affected version and component;
- reproduction steps using synthetic data;
- the likely impact; and
- any suggested containment.

Do not include real credentials, customer data, private source code, or unredacted
receipts. You should receive an acknowledgement within seven days. No bug-bounty
payment is promised.

## Security model

The installed plugin contains fixed adapters for OpenRouter Decisions and TypeSafe
System One. The provider is selected privately during setup and cannot be supplied by
an MCP call. Live requests use bounded payloads, response validation, workspace
policy, pattern-based screening, and local receipts. The enrollment classification
label records owner intent but does not identify ordinary confidential prose.
Automatic prompt shortlisting remains local, and automatic output reduction requires
a local Laya-MLX route. Explicit remote calls transmit their supplied state to the
chosen provider. These controls reduce risk; they are not a hostile-user sandbox,
complete DLP system, compliance certification, or proof that a model judgment is true.

The detailed threat boundaries and operational controls are documented in
[`docs/SECURITY.md`](docs/SECURITY.md).
