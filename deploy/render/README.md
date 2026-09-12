# ChuoSmart on Render (optional Docker prototype)

This deployment path is **only for the team prototype on Render**. It does not
replace, wrap, or modify the existing Namecheap/cPanel deployment.

## Why Namecheap is unaffected

Namecheap continues to start Django through the existing virtualenv/Passenger
workflow with:

```text
DJANGO_ENV=production
```

Docker is never invoked there. `Dockerfile`, `.dockerignore`, `render.yaml` and
`deploy/render/start.sh` are inert files unless a Docker/Render deployment
explicitly uses them.

The only shared settings change is that `Commerce.settings` now recognizes one
additional explicit value:

```text
DJANGO_ENV=render
```

`development` and `production` retain their previous behavior.

## Render architecture

```text
GitHub repository
       |
       v
Render Docker web service
       |
       +--> ChuoSmart Django + Gunicorn + WhiteNoise
       |
       +--> isolated Render Postgres database

Namecheap production
       |
       +--> existing Passenger / Python virtualenv
       +--> existing MySQL database
```

The Render Blueprint never points at the Namecheap database.

## One-click Blueprint setup

1. Push this patch to the branch you want the team to test.
2. In Render choose **New > Blueprint**.
3. Connect the ChuoSmart GitHub repository.
4. Let Render load the root `render.yaml`.
5. Review the resources and apply the Blueprint.

The Blueprint creates:

- `chuosmart-prototype` — Docker web service
- `chuosmart-prototype-db` — separate Render Postgres database

Both are currently configured for Render's free prototype tier and Frankfurt
region.

## What happens on each container start

`deploy/render/start.sh` performs:

1. `python manage.py migrate --noinput`
2. `python manage.py collectstatic --noinput`
3. `python manage.py check`
4. starts Gunicorn on Render's injected `$PORT`

Database migrations can be disabled temporarily with:

```text
RENDER_RUN_MIGRATIONS=false
```

For a single-instance prototype, migrations on start are intentional. For a
future scaled paid deployment, move migrations to Render's pre-deploy command.

## Email behavior

`RENDER_ENABLE_OUTBOUND_EMAIL=false` is the safe prototype default. Django sends
email to the Render logs instead of ChuoSmart's real SMTP account.

This is especially useful on Render's free web plan, where normal SMTP ports are
not available. It also prevents prototype activity from sending marketing or
transactional mail to real users.

## Media/uploads

Render web-service filesystems are ephemeral by default. Static assets are fine
because WhiteNoise rebuilds them at startup, but files written to `media/` or
`private_media/` should be treated as disposable in this prototype.

ChuoSmart's existing Cloudinary-backed upload features can still be configured
with the normal Cloudinary environment variables where applicable. Do not use
this free prototype as permanent storage for user-uploaded files.

## Optional environment variables

Only add external integrations that the team actually needs to test. Examples:

```text
CEREBRAS_API_KEY
SNIPPE_API_KEY
SNIPPE_WEBHOOK_SECRET
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
VAPID_PUBLIC_KEY
VAPID_PRIVATE_KEY
VAPID_ADMIN_EMAIL
```

Do not copy production secrets into the prototype unless there is a specific,
reviewed reason to do so. Test/sandbox credentials are preferred.

## Local Docker smoke test

Build:

```bash
docker build -t chuosmart-render .
```

For a quick local-only smoke test, SQLite can be supplied explicitly as
`DATABASE_URL`:

```bash
docker run --rm -p 8000:8000 \
  -e SECRET_KEY='local-docker-smoke-test-only' \
  -e DATABASE_URL='sqlite:////tmp/chuosmart-render.sqlite3' \
  -e PORT=8000 \
  chuosmart-render
```

Then open:

```text
http://127.0.0.1:8000/
```

This SQLite command is for local smoke testing only. The Render Blueprint uses
Postgres.

## Diagnostics without Docker

With the project's normal virtualenv active:

```bash
DJANGO_ENV=render \
SECRET_KEY='render-diagnostics-only' \
DATABASE_URL='sqlite:////tmp/chuosmart-render-check.sqlite3' \
python manage.py render_diagnostics
```

Then:

```bash
DJANGO_ENV=render \
SECRET_KEY='render-diagnostics-only' \
DATABASE_URL='sqlite:////tmp/chuosmart-render-check.sqlite3' \
python manage.py check
```

## Free-tier prototype limitations

The included Blueprint intentionally uses Render's free tiers because this is a
team prototype, not the production ChuoSmart environment. Expect the following:

- the free web service can spin down after inactivity and take time to wake up;
- its local filesystem is ephemeral;
- free web services do not provide interactive shell/SSH access;
- common outbound SMTP ports are unavailable;
- free Render Postgres is temporary and currently expires after 30 days.

For a longer-lived staging environment, upgrade the database/service plans or
point `DATABASE_URL` at a dedicated non-production database. Never point the
prototype at the live Namecheap database just to make testing easier.

## Test data

A newly created Render Postgres database is empty except for Django migrations.
That is deliberate. Use test accounts and test records, or import a sanitized
non-production dataset. Do not copy credentials, payment secrets, or sensitive
user data into the prototype environment.
