# Upgrading OpenQuant

OpenQuant uses semantic versions. Always upgrade one released minor version at a
time unless the intervening release notes explicitly permit skipping versions.

## Before upgrading

1. Read every intervening entry in `CHANGELOG.md` and the GitHub release notes.
2. Record the running tag with `docker compose images`.
3. Create both the PostgreSQL dump and application-data backup documented in the
   README. Keep them together: saved provider keys require the matching secret
   material from `app_data`.
4. Verify the backup by restoring it into an isolated Compose project before
   changing the primary installation.

## Upgrade a release installation

Set the exact new semantic version—never `latest`—then pull and start it:

```bash
export OPENQUANT_VERSION=0.2.0
docker compose -f docker-compose.yml -f compose.release.yml pull
docker compose -f docker-compose.yml -f compose.release.yml up --no-build -d --wait
docker compose ps
docker compose logs --tail=200 openquant postgres
```

Database migrations run transactionally before the application becomes healthy.
Do not interrupt the first startup. After health succeeds, exercise login, a
credential-free chart, and any workflow named in the release notes.

## Rollback

Application images are immutable, but database migrations are forward-only.
Changing only the image tag after a schema migration is unsupported. To roll
back safely:

1. Stop the stack without deleting volumes.
2. Restore the pre-upgrade PostgreSQL dump and its matching `app_data` backup.
3. Set `OPENQUANT_VERSION` back to the exact previous tag.
4. Start the release Compose files and repeat the health and acceptance checks.

A backup created by a newer release is not assumed compatible with an older
release. Each release must state whether its backup format is compatible with
the immediately previous version.
