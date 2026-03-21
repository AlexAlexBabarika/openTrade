# CI/CD Pipeline Design

## Overview

Expand the existing single-workflow CI (frontend svelte-check only) into a full pipeline covering correctness, style enforcement, build verification, and security scanning across frontend, backend, and Docker.

All workflows trigger on `push` to main and `pull_request` to main. Each workflow uses concurrency control to cancel in-progress runs when new commits are pushed:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

The existing `main.yml` also triggers on `master` — this is intentionally dropped since the repo uses `main`.

## Workflow 1: Frontend (`frontend.yml`)

Replaces current `main.yml`. Three parallel jobs, all using Node 20 with `npm ci` and cache on `package-lock.json`.

| Job | Command | Purpose |
|-----|---------|---------|
| check | `npm run check` | Svelte/TypeScript type checking |
| format | `npx prettier --check .` | Verify formatting (with `.prettierignore`) |
| build | `npm run build` | Ensure production build succeeds |

Working directory: `frontend/`

A `.prettierignore` will be created in `frontend/` (listing `node_modules`, `dist`, `build`, `package-lock.json`) so that `--check .` matches the existing `--write .` dev script. Note: `.prettierrc.json` lives at the repo root and Prettier will find it by walking up.

Path filter: only runs when `frontend/**` or `shared/**` files change.

## Workflow 2: Backend (`backend.yml`)

New workflow. Three parallel jobs using Python 3.12. All jobs run from the repo root.

Setup steps for all jobs:
1. `actions/checkout@v4`
2. `actions/setup-python@v5` with Python 3.12 and pip cache
3. `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` (all jobs need this — mypy needs the production deps to resolve imports, and it keeps setup consistent)

| Job | Command | Purpose |
|-----|---------|---------|
| format | `black --check backend/` | Enforce Python formatting |
| lint | `ruff check backend/` | Fast Python linter (unused imports, syntax issues, common bugs) |
| typecheck | `mypy backend/` | Static type checking |

New dev dependencies to add to `requirements-dev.txt`:
- `ruff>=0.9.0`
- `mypy>=1.14.0`

A basic `mypy.ini` will be created at the repo root with `ignore_missing_imports = True` to avoid failures on third-party packages without type stubs.

A basic `ruff.toml` will be created at the repo root with a limited rule set (E, F — pyflakes and pycodestyle errors) to avoid a flood of findings on the existing codebase. Can be expanded over time.

Note: `black` is already in `requirements-dev.txt`. The codebase should already be black-formatted per the README. If not, an initial formatting commit may be needed before this workflow passes.

Path filter: only runs when `backend/**` or `shared/**` files change.

## Workflow 3: Docker Build (`docker.yml`)

Single job that builds the multi-stage Docker image without pushing. Uses `docker/build-push-action` with `push: false` and Docker layer caching via `docker/setup-buildx-action`.

- Catches broken Dockerfiles, missing dependencies, frontend build failures inside the container

Path filter: runs when `Dockerfile`, `docker-compose.yml`, `frontend/**`, `backend/**`, or `shared/**` change.

## Workflow 4: Security (`security.yml`)

Two parallel jobs for dependency vulnerability scanning.

| Job | Tool | Purpose |
|-----|------|---------|
| npm-audit | `npm audit --omit=dev --audit-level=high` | Flag high/critical production JS dependency vulnerabilities |
| pip-audit | `pip-audit -r backend/requirements.txt` | Flag known Python dependency vulnerabilities |

Setup steps for npm-audit job: `actions/checkout@v4`, `actions/setup-node@v4` with Node 20, `npm ci` in `frontend/` (required for `--omit=dev` to resolve the dependency tree), then `npm audit`.

`npm audit` uses `--omit=dev` to skip devDependency vulnerabilities (common false positives in build tooling like Vite/Rollup transitive deps). `pip-audit` is installed in CI only (`pip install pip-audit`), run from repo root.

Path filter: only runs when `frontend/package.json`, `frontend/package-lock.json`, `backend/requirements.txt`, or `backend/requirements-dev.txt` change.

## Files to Create/Modify

- **Create**: `.github/workflows/frontend.yml`
- **Create**: `.github/workflows/backend.yml`
- **Create**: `.github/workflows/docker.yml`
- **Create**: `.github/workflows/security.yml`
- **Delete**: `.github/workflows/main.yml` (replaced by `frontend.yml`)
- **Modify**: `backend/requirements-dev.txt` (add `ruff>=0.9.0`, `mypy>=1.14.0`)
- **Create**: `mypy.ini` (repo root, basic config with `ignore_missing_imports`)
- **Create**: `ruff.toml` (repo root, limited rule set to start)
- **Create**: `frontend/.prettierignore` (exclude `node_modules`, `dist`, `build`, `package-lock.json`)

## Out of Scope

- Frontend tests (no test files exist yet)
- SAST tools (Semgrep, CodeQL) — overkill for current project size
- Secret scanning — configured as a GitHub repo setting, not a workflow
- Deployment workflows — no deployment target defined yet
