#!/bin/sh

launcher_pause_on_error() {
  if [ "${OPENQUANT_LAUNCHED_FROM_GUI:-0}" = "1" ]; then
    printf '\nPress Return to close this window.'
    read -r _launcher_reply
  fi
}

launcher_fail() {
  printf '\nOpenQuant: %s\n' "$1" >&2
  launcher_pause_on_error
  exit 1
}

launcher_require_docker() {
  command -v docker >/dev/null 2>&1 || launcher_fail \
    "Docker was not found. Install Docker Desktop, then try again."
  docker compose version >/dev/null 2>&1 || launcher_fail \
    "Docker Compose v2 was not found. Update Docker Desktop, then try again."
}

launcher_start_docker() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  printf 'Starting Docker Desktop…\n'
  if docker desktop start >/dev/null 2>&1; then
    :
  elif [ "$(uname -s)" = "Darwin" ]; then
    open -a Docker >/dev/null 2>&1 || launcher_fail \
      "Docker Desktop could not be started. Open it manually, then try again."
  else
    launcher_fail "Docker is not running. Start Docker, then try again."
  fi

  attempts=0
  while ! docker info >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      launcher_fail "Docker did not become ready within two minutes."
    fi
    sleep 2
  done
}

launcher_port_is_published() {
  docker ps --format '{{.Ports}}' 2>/dev/null |
    grep -E "(^|[,[:space:]])(0\\.0\\.0\\.0:|127\\.0\\.0\\.1:|\\[::\\]:|:::)$1->" \
      >/dev/null 2>&1
}

launcher_select_port() {
  candidate=$1
  while [ "$candidate" -le 65535 ]; do
    if ! launcher_port_is_published "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
    candidate=$((candidate + 1))
  done
  return 1
}
