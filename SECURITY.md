# Security policy

## Supported versions

Until OpenQuant reaches a stable `1.0` release, security fixes are provided only
for the latest published release. Upgrade to the newest patch before reporting a
problem that may already have been fixed.

## Reporting a vulnerability

Please do not open a public issue, discussion, or pull request for a suspected
vulnerability. Use GitHub's **Report a vulnerability** button on this
repository's Security page to open a private security advisory. Include:

- the affected version or commit;
- the deployment configuration and required privileges;
- reproduction steps or a minimal proof of concept;
- the impact you observed; and
- any suggested mitigation, if known.

Do not access other people's systems or data, degrade a service, or retain data
obtained during research. We will acknowledge a complete report within seven
days, provide a status update within fourteen days, and coordinate disclosure
after a fix is available. These are best-effort targets for a volunteer-run
project, not a paid bug-bounty commitment.

## Deployment boundary

The default Compose configuration binds OpenQuant only to `127.0.0.1`. It is not
an internet-ready edge deployment. Before exposing it publicly, place it behind
an HTTPS reverse proxy, set `COOKIE_SECURE=1`, configure explicit
`CORS_ORIGINS` only if a separate frontend is required, use unique database
credentials, restrict network access, and maintain backups.

Never include real API keys, passwords, session cookies, tokens, database dumps,
or uploaded trading data in issues or diagnostic logs.
