#!/usr/bin/env bash
set -Eeuo pipefail

export DJANGO_ENV="${DJANGO_ENV:-render}"
export PORT="${PORT:-8000}"

is_true() {
    case "${1:-}" in
        1|true|TRUE|yes|YES|on|ON) return 0 ;;
        *) return 1 ;;
    esac
}

echo "[render] Starting ChuoSmart container"
echo "[render] environment=${DJANGO_ENV} port=${PORT}"

# One free/prototype web instance is expected. Migrations are intentionally
# scoped to the Render database URL; the Namecheap database is never referenced
# by this script.
if is_true "${RENDER_RUN_MIGRATIONS:-true}"; then
    echo "[render] Applying database migrations..."
    python manage.py migrate --noinput
else
    echo "[render] Database migrations skipped (RENDER_RUN_MIGRATIONS=false)."
fi

# Static collection occurs at runtime instead of image-build time so Docker
# builds never need access to DATABASE_URL or any other runtime secret.
echo "[render] Collecting static assets..."
python manage.py collectstatic --noinput

# Fail before accepting traffic if the Django configuration is invalid.
echo "[render] Running Django system check..."
python manage.py check

WORKERS="${GUNICORN_WORKERS:-1}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

printf '[render] Launching gunicorn workers=%s threads=%s timeout=%s\n' \
    "$WORKERS" "$THREADS" "$TIMEOUT"

exec gunicorn Commerce.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "$WORKERS" \
    --threads "$THREADS" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile -
