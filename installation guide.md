## How to run

1. Install [Docker](https://docs.docker.com/get-docker/).
2. Start the application and PostgreSQL from the project directory:

   ```bash
   docker compose up -d --build
   ```

3. Open [http://localhost:8000](http://localhost:8000).

The database schema is installed automatically on the first start and data is
kept in the `postgres_data` Docker volume. OpenTrade generates its own unique
application secrets on first boot and keeps them in the `app_data` volume, so a
`.env` file is not required.

To stop OpenTrade without deleting accounts or settings:

```bash
docker compose down
```

To start it again:

```bash
docker compose up -d
```

To view its status and logs:

```bash
docker compose ps
docker compose logs -f opentrade
```

### Reset all local data

The following command permanently deletes all OpenTrade accounts, saved API
keys, generated secrets, and PostgreSQL data. It cannot be undone unless the
Docker volumes were backed up:

```bash
docker compose down --volumes
```

### Optional configuration

Copy `env.example` to `.env` only when you need to override defaults such as the
browser port or cookie behavior. If you provide `API_KEYS_ENCRYPTION_KEY`, keep
the same value across upgrades and restores; changing it makes existing saved
provider keys unreadable.

For development outside Docker, install `backend/requirements.txt` and
`backend/requirements-dev.txt`, install the frontend packages with `npm install`,
and set `DATABASE_URL` to your PostgreSQL instance.

## Maintenance

```bash
ruff format backend/
cd frontend && npm run format && npm run check
```

Production Python dependencies are declared in `backend/requirements.in` and
locked with hashes in `backend/requirements.txt`. After intentionally changing
the input file, regenerate the lock with:

```bash
pip-compile --generate-hashes --output-file=backend/requirements.txt backend/requirements.in
```
