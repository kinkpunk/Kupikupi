#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kupikupi-smoke}"
KEEP_RUNNING=1

if [ "${1:-}" = "--down" ]; then
  KEEP_RUNNING=0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required." >&2
  exit 1
fi

cleanup() {
  if [ "$KEEP_RUNNING" -eq 0 ]; then
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down --remove-orphans
  fi
}

trap cleanup EXIT

echo "Building and starting Kupikupi smoke stack..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build backend worker scheduler webapp

echo "Waiting for backend readiness..."
attempt=0
until docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/ready', timeout=2).read()"
do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Backend readiness timed out." >&2
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs backend
    exit 1
  fi
  sleep 2
done

echo "Waiting for WebApp..."
attempt=0
until docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T webapp node -e \
  "fetch('http://127.0.0.1:3000').then((response) => process.exit(response.ok ? 0 : 1)).catch(() => process.exit(1))"
do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "WebApp readiness timed out." >&2
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs webapp
    exit 1
  fi
  sleep 2
done

echo "Running backend MVP smoke scenario..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend python scripts/smoke_mvp.py

cat <<EOF

Kupikupi Docker smoke passed.

Backend: http://localhost:8000/v1/ready
WebApp:  http://localhost:3000

EOF

if [ "$KEEP_RUNNING" -eq 1 ]; then
  cat <<EOF
The smoke stack is still running for manual testing.
Stop it with:

  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down --remove-orphans

EOF
fi
