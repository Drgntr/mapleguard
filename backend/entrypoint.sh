#!/bin/sh
echo "=== ENTRYPOINT DEBUG ==="
echo "PORT=${PORT:-8000}"
echo "DATABASE_URL=${DATABASE_URL:+SET}"
echo "ENABLE_SERVICES=${ENABLE_SERVICES:-false}"

# Test imports
echo "--- Testing imports ---"
python -c "
import sys
print(f'[Python] {sys.version}')

try:
    from db.database import engine
    print(f'[OK] Engine URL: {engine.url}')
except Exception as e:
    print(f'[FAIL] DB: {e}', file=sys.stderr)
    sys.exit(1)

try:
    from services.market_data import market_data_service
    print('[OK] market_data')
except Exception as e:
    print(f'[FAIL] market_data: {e}', file=sys.stderr)
    sys.exit(1)

try:
    from routes import items, characters, market, calculator, leaderboard
    print('[OK] routes')
except Exception as e:
    print(f'[FAIL] routes: {e}', file=sys.stderr)
    sys.exit(1)

try:
    from main import app
    print(f'[OK] main app: {app}')
except Exception as e:
    print(f'[FAIL] main app: {e}', file=sys.stderr)
    sys.exit(1)

print('[ALL OK] Ready to start uvicorn')
" || { echo "Import test failed!"; exit 1; }

echo "--- Starting uvicorn ---"
exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --log-level debug \
    --proxy-headers
