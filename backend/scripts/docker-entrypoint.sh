#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  alembic upgrade head
fi

if [ "${RUN_SEED:-0}" = "1" ]; then
  python scripts/seed.py
fi

exec "$@"
