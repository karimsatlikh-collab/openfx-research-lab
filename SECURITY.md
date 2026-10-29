# Security policy

## Scope

OpenFX is a research scaffold. It currently has no deployed VPS worker, broker integration, live-trading path, or production service.

## Reporting a vulnerability

Please do not publish secrets, broker credentials, tokens, private keys, personal data, or exploit details in public issues. Until a private security contact is configured, report only a minimal description through the repository owner's available private GitHub contact channel. If no private channel is available, do not include sensitive details in a public report.

## Security principles

- No credentials in source, manifests, logs, test fixtures, or artifacts.
- No privileged self-hosted GitHub Actions runner on this public repository.
- No arbitrary command execution from public inputs.
- Remote execution remains disabled until reviewed architecture, authentication, authorization, audit logging, and threat-model tests exist.
- Live trading is disabled by default and requires separate explicit authorization.
