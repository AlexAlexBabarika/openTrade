# OpenTrade open-source release checklist

Target experience: a new user with Docker Desktop can download the project, run
`docker compose up -d`, open one documented URL, and use OpenTrade without
editing configuration or administering PostgreSQL. Optional providers and
advanced deployment settings may require configuration, but the default demo
must not.

Definitions used below:

- **P0 — release blocker:** required before the first public release.
- **P1 — release quality:** strongly recommended for the first public release.
- **P2 — follow-up:** useful after the initial release; not a launch blocker.

## P0 — prove the one-command installation

- [x] Make `docker compose up -d` work when no `.env` file exists; auth and saved
  provider keys must be functional out of the box.
- [x] Generate and persist application secrets automatically on first boot, or
  provide another secure zero-input mechanism. Do not ship a shared hard-coded
  secret. Preserve the encryption key across upgrades so stored API keys remain
  decryptable.
- [x] Pass every supported runtime setting through Compose, including
  `COOKIE_SECURE`, `MAX_MARKET_OHLCV_CANDLES`, and the documented rate-limit
  settings.
- [x] Do not publish PostgreSQL port `5432` in the default Compose file. Keep it
  on the internal Compose network; provide a development override if direct DB
  access is useful.
- [x] Add a health check for the `opentrade` service and make `/health` verify a
  database query. The container and database should both become `healthy`.
- [x] Add a restart policy to the application service and verify recovery after
  restarting Docker and after PostgreSQL temporarily becomes unavailable.
- [x] Add a `.dockerignore` that excludes `.git`, `.env`, virtual environments,
  `node_modules`, caches, logs, local datastore contents, editor metadata, and
  test artifacts from the build context.
- [x] Pin base images to maintained patch versions or digests and constrain
  Python dependencies with a reproducible lock/constraints file. Document the
  update process.
- [ ] Test the image and Compose stack on both `linux/amd64` and `linux/arm64`
  (including Apple Silicon).
- [ ] Perform a clean-machine acceptance test using only the public repository:
  clone/download, `docker compose up -d`, wait for health, open the app, load a
  chart using a provider that needs no API key, create an account, sign out and
  in, restart the stack, and confirm data/account persistence.
- [x] Test the destructive path and document it explicitly: stopping containers
  must preserve data; deleting the named volume must be clearly labeled as the
  action that permanently resets OpenTrade.

## P0 — security and safe defaults

- [x] Replace `allow_origins=["*"]` with a configurable allowlist. The default
  single-container deployment should use same-origin requests and need no CORS
  wildcard.
- [x] Bind published ports to `127.0.0.1` by default, or clearly explain that
  binding to all interfaces exposes the service to the local network.
- [x] Validate required secrets and configuration at startup with actionable
  errors; do not leave features to fail later with HTTP 503 responses.
- [x] Review authentication cookies for the supported deployment modes. Document
  that internet exposure requires HTTPS and `COOKIE_SECURE=1`; verify `HttpOnly`,
  `SameSite`, expiry, rotation, logout, and session revocation behavior.
- [x] Authenticate or explicitly disable sensitive WebSocket operations for
  anonymous users. Apply connection/message limits and maximum payload sizes.
- [x] Set upload-size, request-size, timeout, and concurrency limits, especially
  for CSV ingestion, backtests, sweeps, and optimization jobs.
- [x] Ensure logs and API errors never expose passwords, tokens, provider keys,
  database URLs, uploaded data, or stack traces.
- [x] Run secret scanning against the entire Git history, not only the current
  tree. Rotate anything that may previously have been committed.
- [x] Run dependency and container-image vulnerability scans and resolve all
  known critical/high findings or document an explicit, time-bounded exception.
- [x] Run the application as a non-root user in the final image and use a minimal
  writable filesystem area.
- [x] Add `SECURITY.md` with supported versions, a private reporting channel,
  expected response times, and coordinated-disclosure guidance.
- [x] Add an obvious financial disclaimer: educational/research software, not
  investment advice; backtest results do not guarantee future performance; data
  may be delayed or inaccurate.

## P0 — legal and repository essentials

- [x] Choose and add an OSI-approved `LICENSE` file. The repository currently has
  no project license, so others do not have permission to reuse or contribute to
  the code. *(Apache-2.0, plus a `NOTICE` file.)*
- [x] Audit all runtime dependencies, bundled fonts, icons, fixtures, sample
  market data, and branding for redistribution compatibility. Retain required
  notices in a `THIRD_PARTY_NOTICES` file. *(63 backend and 140 frontend
  packages resolved; the missing SIL OFL texts for Lato and Space Mono are now
  bundled beside the fonts.)*
- [x] Confirm that the project name and logo can be used and document trademark
  expectations if necessary. *(`TRADEMARKS.md`. There is no logo, so nothing to
  clear. The name is documented with the third-party OPENTRADE registrations
  found — see the open item below.)*
- [x] Add `CONTRIBUTING.md` with local setup, tests, formatting, issue/PR flow,
  and certificate-of-origin or CLA policy. *(DCO sign-off; every documented
  command was executed and verified.)*
- [x] Add `CODE_OF_CONDUCT.md` and maintainer contact/enforcement details.
  *(Contributor Covenant 2.1 with a reporting process and response targets.)*
- [x] Create issue and pull-request templates, including a security-reporting
  redirect that does not encourage public vulnerability reports. *(Blank issues
  disabled; the security advisory link is the first contact route.)*

Open follow-up from this section:

- [ ] Verify at <https://tsdr.uspto.gov/> whether OPENTRADE serial 78930882
  (Reg. 3244739, Complex Systems, Inc. — financial trade software) is live or
  dead, and update `TRADEMARKS.md`. USPTO's API now requires a key, so this
  could not be confirmed automatically. Low risk for a non-commercial project;
  resolve before any commercial use of the name.

## P0 — replace the README with a user-facing landing page

- [x] Begin with a one-sentence description, a current screenshot/GIF, supported
  use cases, and the project maturity/status.
- [x] Put a **Quick start** near the top: install Docker Desktop, download/clone,
  run `docker compose up -d`, and open `http://localhost:8000`. Configuration
  should be optional for the default experience.
- [x] State supported operating systems, architectures, minimum RAM/disk, and
  whether an internet connection is required for each data provider.
- [x] Clearly distinguish providers that work without credentials from optional
  providers that require user-owned API keys, including links to their terms and
  rate limits.
- [x] Document start, stop, update, backup, restore, reset, logs, and uninstall.
  Keep commands copy/pasteable and explain which operations preserve or delete
  data.
- [x] Document configuration in a compact table: variable, purpose, default,
  allowed format, whether it is secret, and when it is required.
- [x] Explain where user data is stored and what is sent to Yahoo Finance,
  Binance, Twelve Data, or other third parties.
- [ ] Move the current 54-item internal TODO list to the issue tracker or roadmap.
  Several entries are stale (for example, the repository now contains extensive
  backend tests and implementations for indicators, comparisons, portfolios,
  and backtesting).
- [x] Merge or remove `installation guide.md` so setup instructions have one
  canonical source.
- [x] Link the license, contribution guide, security policy, changelog/releases,
  API docs, troubleshooting, and financial disclaimer.

## P1 — operations and upgrades

- [x] Introduce real, ordered database migrations. Files in
  `docker-entrypoint-initdb.d` run only when PostgreSQL initializes an empty
  volume and therefore do not upgrade existing installations.
- [ ] Define and test the supported upgrade path for both images and database
  schema, including rollback and backup compatibility.
- [ ] Publish versioned images to a container registry so ordinary users can run
  Compose without building locally. Never make `latest` the only documented
  version; provide immutable semantic-version tags.
- [ ] Provide separate Compose profiles/override files for local-only defaults,
  development, and HTTPS/reverse-proxy deployment without complicating the basic
  path.
- [ ] Add graceful shutdown and verify in-flight jobs are not corrupted when the
  app is updated or stopped.
- [x] Set log rotation/size limits and document basic diagnostics (`docker compose
  ps` and logs) plus common fixes for occupied ports, unhealthy containers,
  provider failures, and corrupted/old volumes.
- [ ] Document resource expectations and add conservative CPU/memory/job limits
  so a large backtest cannot make a typical desktop unusable.

## P1 — CI and release engineering

- [ ] Add backend test execution to CI. The current backend workflow formats,
  lints, and type-checks but does not run the existing pytest suite.
- [ ] Add frontend unit tests and a non-watch CI command (`vitest run`).
- [ ] Extend Docker CI from image build-only to an actual Compose smoke test:
  start the clean stack, wait for health, exercise the UI/API, restart it, and
  inspect container logs before teardown.
- [ ] Validate the database schema/migrations against a fresh PostgreSQL instance
  in CI and test an upgrade from the previous released version.
- [ ] Add automated dependency updates with grouped, reviewed upgrades.
- [ ] Generate an SBOM and provenance/attestations for release images; sign images
  if the chosen registry supports the intended verification flow.
- [ ] Define semantic versioning, maintain `CHANGELOG.md`, and publish GitHub
  Releases with upgrade notes, breaking changes, checksums, and image tags.
- [ ] Protect the default branch and require relevant tests, security scans, and
  review before merging.

## P1 — product acceptance

- [ ] Verify the app has a useful first-run state with sample/default content and
  no provider key. Empty screens should explain the next action in the UI.
- [ ] Make optional API-key configuration available through the UI; users should
  not need to edit Compose or run database commands.
- [ ] Show actionable provider/network/rate-limit errors without exposing
  internals, and make recovery possible without restarting containers.
- [ ] Test primary workflows in current Chrome, Firefox, Safari, and Edge, plus a
  practical mobile viewport.
- [ ] Run accessibility checks for keyboard navigation, focus order, contrast,
  labels, dialogs, charts, and reduced motion. Document unavoidable chart
  limitations.
- [ ] Verify time zones, currency/unit labels, missing candles, adjusted prices,
  delisted symbols, market closures, and provider disagreements are presented
  without implying false precision.
- [ ] Clearly label simulated/backtested versus live data and prevent any UI copy
  from implying that the software submits real trades unless it actually does.

## P2 — community and project sustainability

- [ ] Publish a concise roadmap based on user outcomes rather than an internal
  implementation backlog.
- [ ] Add architecture and API documentation for contributors, including service
  boundaries, database ownership, and a small data-flow diagram.
- [ ] Label beginner-friendly issues and document how maintainers triage reports.
- [ ] Define the support boundary: community best-effort support, supported
  versions, provider/API limitations, and where questions belong.
- [ ] Add a funding/sponsorship policy only if the project intends to accept it.

## Release gate

The first public release is ready when every P0 item is checked and CI proves the
following from a clean checkout:

1. `docker compose up -d` succeeds with no `.env` and no interactive setup.
2. Both services report healthy and the app opens at the documented URL.
3. A credential-free chart, account lifecycle, persistence, restart, backup, and
   restore flow pass.
4. The repository contains a license, security policy, contribution guide,
   code of conduct, accurate README, and financial/data disclaimers.
5. The tested release tag maps to immutable multi-architecture images and has a
   documented upgrade path.
