# CI/CD Pipeline Design

## Overview

Expand the existing single-workflow CI (frontend svelte-check only) into a full pipeline covering correctness, style enforcement, build verification, and security scanning across frontend, backend, and Docker.

All workflows trigger on `push` to main and `pull_request` to main.

## Workflow 1: Frontend (`frontend.yml`)

Replaces current `main.yml`. Three parallel jobs, all using Node 20 with `npm ci` and cache on `package-lock.json`.

| Job | Command | Purpose |
|-----|---------|---------|
| check | `npm run check` | Svelte/TypeScript type checking |
| format | `npx prettier --check .` | Verify formatting without modifying files |
| build | `npm run build` | Ensure production build succeeds |

Working directory: `frontend/`

## Workflow 2: Backend (`backend.yml`)

New workflow. Three parallel jobs using Python 3.12.

| Job | Command | Purpose |
|-----|---------|---------|
| format | `black --check backend/` | Enforce Python formatting |
| lint | `ruff check backend/` | Fast Python linter (unused imports, syntax issues, common bugs) |
| typecheck | `mypy backend/` | Static type checking |

New dev dependencies to add to `requirements-dev.txt`:
- `ruff`
- `mypy`

A basic `mypy.ini` will be created with `ignore_missing_imports = True` to avoid failures on third-party packages without type stubs.

## Workflow 3: Docker Build (`docker.yml`)

Single job that builds the multi-stage Docker image without pushing. Verifies the Dockerfile, dependency installation, and frontend build all succeed inside the container.

- Uses `docker build .` with GitHub Actions cache
- Catches broken Dockerfiles, missing dependencies, frontend build failures

## Workflow 4: Security (`security.yml`)

Two parallel jobs for dependency vulnerability scanning.

| Job | Tool | Purpose |
|-----|------|---------|
| npm-audit | `npm audit --audit-level=high` | Flag high/critical JS dependency vulnerabilities |
| pip-audit | `pip-audit -r backend/requirements.txt` | Flag known Python dependency vulnerabilities |

`npm audit` uses `--audit-level=high` to avoid noise from moderate/low findings. `pip-audit` is installed in CI only (not added to project deps).

## Files to Create/Modify

- **Create**: `.github/workflows/frontend.yml`
- **Create**: `.github/workflows/backend.yml`
- **Create**: `.github/workflows/docker.yml`
- **Create**: `.github/workflows/security.yml`
- **Delete**: `.github/workflows/main.yml` (replaced by `frontend.yml`)
- **Modify**: `backend/requirements-dev.txt` (add `ruff`, `mypy`)
- **Create**: `mypy.ini` (basic config with `ignore_missing_imports`)

## Out of Scope

- Frontend tests (no test files exist yet)
- SAST tools (Semgrep, CodeQL) — overkill for current project size
- Secret scanning — configured as a GitHub repo setting, not a workflow
- Deployment workflows — no deployment target defined yet
