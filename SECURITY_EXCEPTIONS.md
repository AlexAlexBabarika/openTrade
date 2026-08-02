# Time-bounded security exceptions

## Starlette 0.52.1 — expires 2026-09-01

The dependency audit reports `PYSEC-2026-161`, `PYSEC-2026-248`,
`PYSEC-2026-249`, `PYSEC-2026-2280`, and `PYSEC-2026-2281`. Their patched
Starlette releases are 1.x, while the latest tested FastAPI release (`0.141.1`)
still constrains Starlette to `<0.53.0`. Forcing Starlette 1.x would install an
unsupported framework combination.

The container scan maps two of these to `CVE-2026-48818` (UNC paths in
`StaticFiles`) and `CVE-2026-54283` (URL-encoded form limits). The UNC behavior
is not reachable in the Linux image. OpenTrade rejects declared HTTP bodies
over 12 MiB and reads uploads through a separate 10 MiB cap, reducing the form
denial-of-service exposure. The service remains bound to localhost by default.

Temporary mitigations:

- `TrustedHostMiddleware` rejects malformed and unlisted Host headers;
- `ALLOWED_HOSTS` rejects wildcards and defaults to local-only hostnames;
- the default Docker port binds only to `127.0.0.1`;
- authentication uses route dependencies and bearer tokens, not
  `request.url` path-based middleware; and
- internet-facing deployments are instructed to use a validating HTTPS reverse
  proxy.

Review this exception weekly and remove the audit ignores as soon as FastAPI
supports a patched Starlette release. The exception must not be renewed without
documenting upstream compatibility and re-evaluating exposure.
