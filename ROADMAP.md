# OpenTrade roadmap

This roadmap replaces the implementation-oriented 54-item TODO list formerly
embedded in the README. Priorities are expressed as user outcomes; implementation
choices remain open until an issue or design proposal is accepted.

## Reliable self-hosting

Users should be able to install, operate, observe, upgrade, and recover OpenTrade
without becoming database administrators. Near-term work includes a supported
upgrade and rollback policy, resource controls for expensive jobs, structured
diagnostics, API stability/versioning, durable market-data caching where it
materially improves the experience, and production scaling only when real usage
requires distributed caching, rate limiting, or job queues.

Legacy TODOs: 1–7, 11–13, 40–46. Items 8–10 are complete; item 41's development
services remain optional and must not complicate the default installation.

## Better market exploration

Users should be able to find, compare, annotate, and export instruments while
understanding data freshness and limitations. Candidate outcomes include richer
live data, saved watchlists, symbol discovery and filtering, drawing and notes,
alerts, export, additional providers, timezone controls, volume profile, and a
long-range overview.

Legacy TODOs: 14–24 and 33–35. Indicators, comparisons, volume profile, and
several export paths now exist; follow-up work should start from current product
gaps rather than recreate those completed features.

## A polished interface

The main workflows should be responsive, accessible, fast, and understandable
across supported browsers. Candidate outcomes include explicit theme and chart
controls, mobile layouts, keyboard operation, non-disruptive progress and error
feedback, persistent preferences, and smaller initial downloads. Offline/PWA
behavior should be pursued only with a clear data-freshness model.

Legacy TODOs: 25–32, 47, and 48.

## Trustworthy research workflows

Users should be able to reproduce simulations, distinguish them from live data,
and understand risk and provenance. Portfolio simulation and backtesting are now
substantial product areas. Remaining proposals—paper trading, news, and sharing—
need explicit privacy, licensing, and “not a brokerage” boundaries before work
begins.

Legacy TODOs: 49–54. Portfolio tracking and backtesting (49 and 51) are
implemented in their current research-oriented form. Internationalization remains
a valid accessibility goal; paper trading, news, and social features are not
committed release scope.

## Engineering confidence

Every supported workflow should have proportionate automated coverage and useful
API documentation. Backend tests now exist, as do frontend unit tests and Docker
smoke coverage. The remaining release work is to run those suites consistently in
CI, validate migrations and upgrades against PostgreSQL, and add browser-level
acceptance coverage for critical user journeys.

Legacy TODOs: 36–39 and 43. This section is tracked concretely in
`RELEASE_CHECKLIST.md` until the first public release.

## How work enters the roadmap

Open an issue describing the user problem, evidence that it matters, acceptance
criteria, and relevant security or data-provider constraints. An item appearing
above is a direction, not a promise or an approved implementation design.
