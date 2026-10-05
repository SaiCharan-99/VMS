#!/usr/bin/env bash
# One-command local setup for macOS / Linux.
#   bash scripts/setup.sh [--no-demo] [--no-ml]
# Creates .env with random secrets (if missing), builds and starts the Docker stack, and creates
# demo logins. Safe to re-run: an existing .env and existing users are kept.
set -euo pipefail
cd "$(dirname "$0")/.."

NO_DEMO=0
NO_ML=0
for arg in "$@"; do
  case "$arg" in
    --no-demo) NO_DEMO=1 ;;
    --no-ml) NO_ML=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }
secret() { head -c "$1" /dev/urandom | base64 | tr -d '+/=\n'; }
port_free() { ! (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
first_free() {
  for p in "$@"; do port_free "$p" && { echo "$p"; return; }; done
  fail "None of the ports $* is free."
}
set_env() {
  if grep -q "^$1=" .env; then
    sed -i.bak "s|^$1=.*|$1=$2|" .env && rm -f .env.bak
  else
    echo "$1=$2" >> .env
  fi
}

step "Checking Docker"
command -v docker >/dev/null || fail "Docker is not installed: https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 || fail "Docker is installed but not running. Start it and re-run."

step "Preparing .env"
if [ -f .env ]; then
  echo ".env already exists: keeping it."
else
  cp .env.example .env
  set_env VMS_JWT_SECRET "$(secret 48)"
  set_env POSTGRES_PASSWORD "$(secret 24)"
  set_env VMS_HTTP_PORT "$(first_free 80 8080 8081 8888)"
  set_env VMS_API_PORT "$(first_free 8000 18000 18001)"
  set_env VMS_PG_PORT "$(first_free 5432 55432 55433)"
  echo "Created .env with random secrets."
fi
[ "$NO_ML" = 1 ] && set_env WITH_ML 0
HTTP_PORT="$(grep -m1 '^VMS_HTTP_PORT=' .env | cut -d= -f2)"
HTTP_PORT="${HTTP_PORT:-80}"

step "Building and starting the stack (first run downloads ML libraries: 5-15 min)"
if ! docker compose up -d --build --wait; then
  docker compose logs --tail 50
  fail "The stack did not become healthy (logs above)."
fi

if [ "$NO_DEMO" = 0 ]; then
  step "Creating demo logins"
  docker compose exec -T api python -m vms.cli seed-demo
fi

URL="http://localhost"; [ "$HTTP_PORT" != 80 ] && URL="http://localhost:$HTTP_PORT"
printf '\nVMS SOP Analyzer is running at %s\n' "$URL"
echo "API docs: $URL/docs    Stop: docker compose down    Logs: docker compose logs -f"
