# Database migrations

OpenTrade applies these PostgreSQL migrations during application startup, before
the service becomes ready. Each migration and its ledger entry commit in the
same transaction, and an advisory lock prevents two app instances from migrating
concurrently.

Migration files must be named `<version>_<name>.sql`, for example
`002_add_watchlists.sql`. Versions are positive, unique integers and run in
numeric order.

Applied files are immutable: OpenTrade stores their SHA-256 checksums and refuses
to start if an applied file changes. Fixes must be added as a new migration.
Before releasing a migration, test both paths:

1. Apply every migration to an empty PostgreSQL database.
2. Back up a database from the previous release, start the new version against a
   copy, and verify the application and data before publishing.

Migration `001` is also the baseline for databases created by the former
`docker-entrypoint-initdb.d` setup. The migrator verifies all legacy tables are
present before recording that baseline; it refuses partially initialized
schemas.
