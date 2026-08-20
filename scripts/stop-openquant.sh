#!/bin/sh

set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")
cd -- "$PROJECT_DIR" || exit 1

. "$SCRIPT_DIR/launcher-common.sh"
launcher_require_docker
launcher_start_docker

printf 'Stopping OpenQuant…\n'
if ! docker compose stop; then
  launcher_fail "OpenQuant could not be stopped. Review the message above."
fi

printf '\nOpenQuant is stopped. Your accounts, settings, and data were preserved.\n'
