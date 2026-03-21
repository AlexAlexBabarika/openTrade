# CI/CD Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single frontend-only CI workflow with a full pipeline covering frontend, backend, Docker, and security checks.

**Architecture:** Four independent GitHub Actions workflow files, each with parallel jobs and path-based filtering. Supporting config files (mypy.ini, ruff.toml, .prettierignore) and updated dev dependencies.

**Tech Stack:** GitHub Actions, Node 20, Python 3.12, black, ruff, mypy, prettier, svelte-check, vite, docker/build-push-action, npm audit, pip-audit

**Spec:** `docs/superpowers/specs/2026-03-21-cicd-pipeline-design.md`

---

### Task 1: Create frontend .prettierignore

**Files:**
- Create: `frontend/.prettierignore`

- [ ] **Step 1: Create the .prettierignore file**

```
node_modules
dist
build
package-lock.json
```

- [ ] **Step 2: Verify prettier still works with the ignore file**

Run: `cd frontend && npx prettier --check "src/**"`
Expected: Either all files pass, or it lists files needing formatting (no errors about scanning node_modules).

- [ ] **Step 3: Commit**

```bash
git add frontend/.prettierignore
git commit -m "chore: add .prettierignore to frontend"
```

---

### Task 2: Add backend dev dependencies and config files

**Files:**
- Modify: `backend/requirements-dev.txt`
- Create: `mypy.ini` (repo root)
- Create: `ruff.toml` (repo root)

- [ ] **Step 1: Add ruff and mypy to requirements-dev.txt**

Append to `backend/requirements-dev.txt`:
```
ruff>=0.9.0
mypy>=1.14.0
```

- [ ] **Step 2: Create mypy.ini at repo root**

```ini
[mypy]
ignore_missing_imports = True
```

- [ ] **Step 3: Create ruff.toml at repo root**

```toml
[lint]
select = ["E", "F"]
```

- [ ] **Step 4: Install and verify tools work locally**

Run: `pip install -r backend/requirements-dev.txt`
Then: `black --check backend/`
Then: `ruff check backend/`
Then: `mypy backend/`

If black or ruff report existing issues, fix them before proceeding (this may require a formatting pass with `black backend/` and/or fixing ruff findings).

- [ ] **Step 5: Commit**

```bash
git add backend/requirements-dev.txt mypy.ini ruff.toml
git commit -m "chore: add ruff, mypy config and dev dependencies"
```

If code fixes were needed in step 4:
```bash
git add backend/
git commit -m "style: fix existing black/ruff findings in backend"
```

---

### Task 3: Create frontend workflow

**Files:**
- Create: `.github/workflows/frontend.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - 'shared/**'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'
      - 'shared/**'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run check

  format:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx prettier --check .

  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/frontend.yml'))"`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/frontend.yml
git commit -m "ci: add frontend workflow with check, format, and build jobs"
```

---

### Task 4: Create backend workflow

**Files:**
- Create: `.github/workflows/backend.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Backend

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - 'shared/**'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'
      - 'shared/**'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: black --check backend/

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: ruff check backend/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: mypy backend/
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/backend.yml'))"`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/backend.yml
git commit -m "ci: add backend workflow with format, lint, and typecheck jobs"
```

---

### Task 5: Create Docker build workflow

**Files:**
- Create: `.github/workflows/docker.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    paths:
      - 'Dockerfile'
      - 'docker-compose.yml'
      - 'frontend/**'
      - 'backend/**'
      - 'shared/**'
  pull_request:
    branches: [main]
    paths:
      - 'Dockerfile'
      - 'docker-compose.yml'
      - 'frontend/**'
      - 'backend/**'
      - 'shared/**'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docker.yml'))"`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docker.yml
git commit -m "ci: add Docker build verification workflow"
```

---

### Task 6: Create security workflow

**Files:**
- Create: `.github/workflows/security.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Security

on:
  push:
    branches: [main]
    paths:
      - 'frontend/package.json'
      - 'frontend/package-lock.json'
      - 'backend/requirements.txt'
      - 'backend/requirements-dev.txt'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/package.json'
      - 'frontend/package-lock.json'
      - 'backend/requirements.txt'
      - 'backend/requirements-dev.txt'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  npm-audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm audit --omit=dev --audit-level=high

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/security.yml'))"`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci: add security workflow with npm audit and pip-audit"
```

---

### Task 7: Delete old main.yml workflow

**Files:**
- Delete: `.github/workflows/main.yml`

- [ ] **Step 1: Verify frontend.yml exists and covers main.yml's functionality**

Run: `ls .github/workflows/frontend.yml`
Expected: File exists.

The `check` job in `frontend.yml` replaces the `check` job from `main.yml`.

- [ ] **Step 2: Delete main.yml**

Run: `rm .github/workflows/main.yml`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/main.yml
git commit -m "ci: remove old main.yml workflow (replaced by frontend.yml)"
```
