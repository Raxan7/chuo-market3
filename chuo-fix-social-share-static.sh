#!/usr/bin/env bash
# ChuoSmart static asset deployment helper for Django/WhiteNoise or cPanel static hosting.
# Run from the Django project root with the correct virtual environment activated.
set -Eeuo pipefail

usage() {
  cat <<'HELP'
Usage:
  bash chuo-fix-social-share-static.sh [--web-root /absolute/path/to/site/document-root] [--url https://chuosmart.com]

Defaults to Django collectstatic only. If the production web server intercepts
/static/ before Django, pass its VERIFIED document root with --web-root to
install ONLY the two public sharing assets under WEB_ROOT/static/app/...

This script does NOT change databases, payout configuration, or Git files.
It does not remove or overwrite unrelated static files.
HELP
}

WEB_ROOT=''
SITE_URL='https://chuosmart.com'
while (( $# > 0 )); do
  case "$1" in
    --web-root)
      if (( $# < 2 )); then echo 'Missing --web-root value' >&2; exit 2; fi
      WEB_ROOT=$2; shift 2;;
    --url)
      if (( $# < 2 )); then echo 'Missing --url value' >&2; exit 2; fi
      SITE_URL=${2%/}; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done

[[ -f manage.py ]] || { echo 'ERROR: Run from Django project root (manage.py missing).' >&2; exit 1; }
for asset in app/css/social-share.css app/js/social-share.js; do
  [[ -s "static/$asset" ]] || {
    echo "ERROR: Source static/$asset is missing or empty. Deploy/commit the sharing files first." >&2
    exit 1
  }
done

echo '[1/4] Discovering Django static files...'
python manage.py findstatic app/css/social-share.css --verbosity 0 >/dev/null
python manage.py findstatic app/js/social-share.js --verbosity 0 >/dev/null

echo '[2/4] Collecting static assets...'
python manage.py collectstatic --noinput

STATIC_ROOT=$(python manage.py shell -c 'from django.conf import settings; print(settings.STATIC_ROOT)' | tail -n 1)
[[ -n "$STATIC_ROOT" && "$STATIC_ROOT" = /* ]] || {
  echo "ERROR: STATIC_ROOT is not a usable absolute path: $STATIC_ROOT" >&2; exit 1;
}
for asset in app/css/social-share.css app/js/social-share.js; do
  [[ -s "$STATIC_ROOT/$asset" ]] || {
    echo "ERROR: collectstatic did not create $STATIC_ROOT/$asset" >&2
    exit 1
  }
done
echo "Collected assets verified under: $STATIC_ROOT"

if [[ -n "$WEB_ROOT" ]]; then
  [[ "$WEB_ROOT" = /* && -d "$WEB_ROOT" ]] || {
    echo 'ERROR: --web-root must name an EXISTING absolute document-root directory.' >&2
    exit 2
  }
  ROOT_REAL=$(cd "$WEB_ROOT" && pwd -P)
  [[ "$ROOT_REAL" != '/' ]] || {
    echo 'ERROR: Refusing to copy into filesystem root.' >&2; exit 2;
  }
  echo "[3/4] Copying ONLY social-share assets to $ROOT_REAL/static/..."
  install -D -m 0644 "$STATIC_ROOT/app/css/social-share.css" "$ROOT_REAL/static/app/css/social-share.css"
  install -D -m 0644 "$STATIC_ROOT/app/js/social-share.js" "$ROOT_REAL/static/app/js/social-share.js"
else
  echo '[3/4] No --web-root provided; no assets were copied outside STATIC_ROOT.'
  echo 'If public URLs still return 404 on cPanel, check your actual domain document root in cPanel.'
  echo 'Rerun with --web-root /verified/absolute/document/root if Apache serves /static/ directly.'
fi

printf '[4/4] Checking remote HTTP responses (best effort)...\n'
if command -v curl >/dev/null 2>&1; then
  for asset in app/css/social-share.css app/js/social-share.js; do
    url="$SITE_URL/static/$asset"
    response=$(curl --silent --show-error --location --max-time 15 \
      --output /dev/null --write-out '%{http_code} %{content_type}' "$url") || response='unreachable'
    printf '%s -> %s\n' "$url" "$response"
  done
else
  echo 'curl not installed; open the two URLs manually and verify 200 + correct Content-Type.'
fi

echo 'DONE. If URLs still serve HTML/404, investigate CDN cache, public docroot,'
echo 'or Apache/Passenger routing before changing Django code.'
