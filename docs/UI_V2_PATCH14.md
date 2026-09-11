# ChuoSmart UI v2 — Patch 14

Patch 14 repositions the public ChuoSmart experience for enterprise credibility while preserving the existing Django business logic, LMS, jobs, marketplace, authentication and payment flows.

## What changes

- New premium global navigation and footer.
- New company front door at `/`.
- New ad-free enterprise landing page at `/for-business/`.
- New flagship product page at `/for-business/ai-workforce-accelerator/`.
- Responsive design system under the unique `static/chuosmart_v2/` namespace.
- Existing course, job, marketplace and materials routes remain unchanged.
- Homepage and business surfaces are ad-free; eligible content/marketplace surfaces keep existing ad behavior.
- Static sitemap includes the two new enterprise pages.

## Production safety

There is no database migration in this patch. The new public business pages do not depend on enterprise cohort models, so they are safe to deploy independently from the enterprise backend release.

## Validation

Before deployment run:

```bash
DJANGO_ENV=development python manage.py check
DJANGO_ENV=development python manage.py test core.test_ui_v2
DJANGO_ENV=development python manage.py test core.tests jobs.tests lms.tests
DJANGO_ENV=development python manage.py ui_diagnostics
```

Then in production:

```bash
git pull origin main
python manage.py check
python manage.py ui_diagnostics
python manage.py collectstatic --noinput
touch tmp/restart.txt
```

No `migrate` is required for Patch 14.

## Release hardening completed

The final Patch 14 release also fixes defects surfaced by the full regression gate:

- paid course/module views no longer shadow Django's translation function with `get_or_create()` booleans;
- completed Snippe module-payment callbacks/webhooks grant access without HTTP 500s and remain idempotent;
- when `CEREBRAS_STRICT_ASSESSMENTS=False` and no provider key is available, deterministic module assessments keep learning usable instead of failing the learner journey;
- learner-specific fallback assessments remain idempotent and module progress continues to resolve the correct personal assessment;
- module purchase and pending-payment states now show clear professional copy and stable two-decimal TZS pricing.

Final local release gate on the uploaded codebase:

- `121/121` focused regression tests passing (`core.tests`, `jobs.tests`, `lms.tests`, `core.test_ui_v2`);
- `python manage.py ui_diagnostics` passing;
- `collectstatic --noinput --clear`: `417` files copied, no duplicate-path warnings;
- `git diff --check` clean;
- no database migration required.
