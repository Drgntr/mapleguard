#!/bin/sh
set -e

echo "=== RAILWAY ENTRYPOINT DEBUG ==="
echo "DATABASE_URL: ${DATABASE_URL:-NOT SET}"
echo "PORT: ${PORT:-8000}"
echo "MSU_OPENAPI_KEY: ${MSU_OPENAPI_KEY:+SET (hidden)}"

# Quick import test
python -c "
import sys
try:
    from db.database import init_db, engine
    print(f'[DB] Engine URL: {engine.url}')
except Exception as e:
    print(f'[DB] INIT FAILED: {e}', file=sys.stderr)
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "[OK] Database module loaded successfully"
fi

echo "[Starting] uvicorn on port ${PORT:-8000}..."
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info --proxy-headers
