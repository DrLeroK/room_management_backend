#!/bin/sh
set -e

echo "==> [Docker Entrypoint] Starting StayCraft Room Management Backend..."

# 1. Validate & Probe PostgreSQL Database Connection
if [ -z "$DATABASE_URL" ]; then
  echo "==> [Docker Entrypoint] WARNING: DATABASE_URL is not set. Proceeding with default/fallback database."
else
  echo "==> [Docker Entrypoint] Waiting for database connection to be ready..."
  RETRY_COUNT=0
  MAX_RETRIES=30

  until python3 -c "
import sys, os, urllib.parse
import socket

db_url = os.environ.get('DATABASE_URL', '')
if not db_url or 'sqlite' in db_url:
    sys.exit(0)

# Replace postgres:// with postgresql:// for compatibility
if db_url.startswith('postgres://'):
    db_url = 'postgresql://' + db_url[11:]

res = urllib.parse.urlparse(db_url)
host = res.hostname or 'localhost'
port = res.port or 5432

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((host, port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
      echo "==> [Docker Entrypoint] WARNING: Database probe timed out ($MAX_RETRIES attempts). Attempting Django startup..."
      break
    fi
    echo "    Database unavailable - attempt $RETRY_COUNT/$MAX_RETRIES - sleeping 2s..."
    sleep 2
  done
  echo "==> [Docker Entrypoint] Database connectivity check passed!"
fi

# 2. Apply Database Migrations
echo "==> [Docker Entrypoint] Running database migrations..."
python manage.py migrate --noinput

# 3. Ensure Database Cache Table Exists for Rate Limiting
echo "==> [Docker Entrypoint] Ensuring cache table exists..."
python manage.py createcachetable 2>/dev/null || true

# 4. Collect Static Files (Production Static Asset Optimization)
echo "==> [Docker Entrypoint] Collecting static assets..."
python manage.py collectstatic --noinput

# 5. Optional Automatic Database Seeding
if [ "$SEED_DATABASE" = "true" ] || [ "$SEED_DATABASE" = "1" ]; then
  echo "==> [Docker Entrypoint] Seeding database with demo system accounts and rooms..."
  python manage.py seed_db || echo "==> [Docker Entrypoint] Seeding finished or records already exist."
fi

echo "==> [Docker Entrypoint] Starting StayCraft server on port ${PORT:-8000}..."
exec "$@"
