# Security Policy

## Supported Versions

Security fixes target the latest 0.1.x release. This is an early-stage local tool,
not a security isolation product.

## Trust Model

Configured commands run with the current user's permissions and environment.
The runner does not implement a sandbox, network restrictions, credential
filtering, or memory limits. Only run commands and workspaces you trust.

Artifact paths are checked against the attempt directory. These checks constrain
what the runner records; they do not restrict what a subprocess can access.
SQLite and SHA-256 manifests provide local bookkeeping and change detection, not
tamper-proof attestation or authenticated provenance.

On POSIX systems, normal completion, timeout and caught interruption trigger
process-group cleanup. A process can escape its group. Windows cleanup only
targets the direct child. Uncatchable termination may leave processes running.
Inspect local processes before recovering a crashed run.

## Data Handling

The package itself has no network client or telemetry. User commands may have
both. Logs and metrics may contain sensitive data; they remain local and should
not be committed or attached to an issue without review.

## Private Reports

Use GitHub's private vulnerability reporting form:
https://github.com/Chengyuann/evidence-loop/security/advisories/new

Do not publish credentials, exploit output containing private data, or live
internal endpoints. Include the affected version and a minimal synthetic
reproduction. No response-time SLA or bug bounty is promised.
