# Security policy

## Supported release

Security fixes are applied to the latest tagged release. The global plugin can call
the user-selected Jev provider, but only after a human creates an expiring grant for
the exact workspace and reviewed repository revision.

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
an MCP call. Live requests use bounded payloads, response validation, data
classification, provider-bound and workspace-bound grants, and local receipts. These
controls reduce risk; they are not a hostile-user sandbox, complete DLP system,
compliance certification, or proof that a model judgment is true.

The detailed threat boundaries and operational controls are documented in
[`docs/SECURITY.md`](docs/SECURITY.md).
