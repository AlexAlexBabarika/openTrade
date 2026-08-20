<!--
Do not use a pull request to report or fix an undisclosed security
vulnerability. A public patch discloses the flaw before users can upgrade.
Report it privately first — see SECURITY.md.
-->

## What does this change?

<!-- Describe the change and why it is needed. Link the issue it addresses. -->

Closes #

## How was it verified?

<!--
Say what you actually ran, and what the result was. "Should work" is not
verification. Paste the relevant output if a suite is involved.
-->

## Checks

<!-- Tick what applies to the areas you touched. Delete the rest. -->

Backend:

- [ ] `ruff format backend/`
- [ ] `ruff check backend/`
- [ ] `mypy backend/`
- [ ] `pytest backend/tests`

Frontend:

- [ ] `npm --prefix frontend run check`
- [ ] `npx --prefix frontend prettier --check --ignore-unknown frontend/`
- [ ] `npx --prefix frontend vitest run --root frontend`
- [ ] `npm --prefix frontend run build`

## Checklist

- [ ] Commits are signed off (`git commit -s`) per the [DCO](CONTRIBUTING.md#developer-certificate-of-origin).
- [ ] The change is focused — no unrelated refactors or formatting sweeps.
- [ ] Tests cover the new behaviour, or a regression test reproduces the bug.
- [ ] No secrets, API keys, `.env` files, or real account data are included.
- [ ] Documentation is updated if behaviour or configuration changed.
- [ ] New dependencies are noted below and added to `THIRD_PARTY_NOTICES.md`.

## New dependencies

<!--
List any added dependency with its license, or write "none".
Copyleft licenses (GPL, AGPL, LGPL, MPL) need discussion before merge —
they create redistribution obligations for everyone shipping the image.
-->

none

## Breaking changes

<!--
Describe anything that changes existing behaviour, configuration, or stored
data, and what users must do when upgrading. Write "none" if not applicable.
-->

none
