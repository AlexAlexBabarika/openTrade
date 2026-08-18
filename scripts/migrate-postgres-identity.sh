#!/bin/sh

set -eu

new_user=${POSTGRES_USER:?POSTGRES_USER is required}
new_database=${POSTGRES_DB:?POSTGRES_DB is required}
new_password=${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
legacy_user=${LEGACY_POSTGRES_USER:-opentrade}
legacy_database=${LEGACY_POSTGRES_DB:-opentrade}
legacy_password=${LEGACY_POSTGRES_PASSWORD:-opentrade}

validate_identifier() {
  case "$2" in
    ''|[0-9]*|*[!A-Za-z0-9_]*)
      printf '%s must be a PostgreSQL identifier, got: %s\n' "$1" "$2" >&2
      exit 1
      ;;
  esac
}

validate_identifier POSTGRES_USER "$new_user"
validate_identifier POSTGRES_DB "$new_database"
validate_identifier LEGACY_POSTGRES_USER "$legacy_user"
validate_identifier LEGACY_POSTGRES_DB "$legacy_database"

can_connect() {
  PGPASSWORD=$1 psql \
    --host postgres \
    --username "$2" \
    --dbname "$3" \
    --no-psqlrc \
    --tuples-only \
    --command 'SELECT 1' >/dev/null 2>&1
}

if can_connect "$new_password" "$new_user" "$new_database"; then
  printf 'PostgreSQL identity is already current.\n'
  exit 0
fi

admin_password=$new_password
if ! can_connect "$admin_password" "$legacy_user" postgres; then
  admin_password=$legacy_password
fi

if ! can_connect "$admin_password" "$legacy_user" postgres; then
  printf '%s\n' \
    'Could not authenticate with either the current or legacy PostgreSQL credentials.' \
    'If the old installation used a custom password, set LEGACY_POSTGRES_PASSWORD to that value.' >&2
  exit 1
fi

printf 'Migrating the PostgreSQL login and database identity…\n'
PGPASSWORD=$admin_password psql \
  --host postgres \
  --username "$legacy_user" \
  --dbname postgres \
  --no-psqlrc \
  --set ON_ERROR_STOP=1 \
  --set new_user="$new_user" \
  --set new_database="$new_database" \
  --set new_password="$new_password" \
  --set legacy_database="$legacy_database" <<'SQL'
SELECT format(
  'CREATE ROLE %I WITH LOGIN SUPERUSER PASSWORD %L',
  :'new_user',
  :'new_password'
)
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'new_user') \gexec

SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :'legacy_database'
  AND pid <> pg_backend_pid();

SELECT format('ALTER DATABASE %I RENAME TO %I', :'legacy_database', :'new_database')
WHERE EXISTS (SELECT FROM pg_database WHERE datname = :'legacy_database')
  AND NOT EXISTS (SELECT FROM pg_database WHERE datname = :'new_database') \gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', :'new_database', :'new_user')
WHERE EXISTS (SELECT FROM pg_database WHERE datname = :'new_database') \gexec
SQL

if ! can_connect "$new_password" "$new_user" "$new_database"; then
  printf 'PostgreSQL identity migration completed but verification failed.\n' >&2
  exit 1
fi

printf 'PostgreSQL identity migration completed.\n'
