#!/usr/bin/env sh
set -e

# Wait for DB if DATABASE_URL points to db service
if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  # simple wait loop (10 * 1s)
  i=0
  until alembic current >/dev/null 2>&1 || [ $i -ge 20 ]; do
    i=$((i+1))
    sleep 1
  done
fi

# Run migrations (idempotent)
alembic upgrade head || true

# Start API
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
