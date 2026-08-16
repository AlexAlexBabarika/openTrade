#!/bin/sh

set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
cd -- "$PROJECT_DIR" || exit 1

. "$SCRIPT_DIR/launcher-common.sh"
launcher_require_docker
launcher_start_docker

printf 'Starting OpenTrade…\n'
if ! docker compose up -d --wait --wait-timeout 180; then
  printf '\nRecent container logs:\n' >&2
  docker compose logs --tail=100 >&2
  launcher_fail "Startup failed. Review the messages above for the cause."
fi

published_address=$(docker compose port opentrade 8000 2>/dev/null | head -n 1)
published_port=${published_address##*:}
case "$published_port" in
  ''|*[!0-9]*) published_port=8000 ;;
esac
app_url="http://localhost:${published_port}"

printf '\nOpenTrade is ready at %s\n' "$app_url"
case "$(uname -s)" in
  Darwin) open "$app_url" >/dev/null 2>&1 || true ;;
  Linux)
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$app_url" >/dev/null 2>&1 || true
    fi
    ;;
esac
