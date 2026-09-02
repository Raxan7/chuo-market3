# ChuoSmart production deployment runbook

This runbook accompanies the August 2026 hardening patches. Commands assume the
repository is already deployed and a Python virtual environment is available.
Do not store production passwords or API keys in Git.

## 1. Required environment

Set `DJANGO_ENV=production` explicitly. Production startup now refuses to fall
back to development settings. At minimum configure:

- `SECRET_KEY`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SUPPORT_EMAIL_HOST_PASSWORD`
- `ADMIN_EMAIL` (where employer-verification alerts should go)
- `SNIPPE_API_KEY`, `SNIPPE_WEBHOOK_SECRET`

Use `env.production.example` as the non-secret reference.

## 2. Deployment sequence

```bash
python -m pip install -r requirements.txt
export DJANGO_ENV=production
python manage.py check
python manage.py check --deploy
python manage.py migrate
python manage.py migrate_private_payment_proofs --dry-run
python manage.py migrate_private_payment_proofs
python manage.py collectstatic --noinput
python manage.py test core.tests jobs.tests
```

Restart the WSGI/Gunicorn application after migrations and static collection.

## 3. Email diagnostics

```bash
python manage.py email_diagnostics
python manage.py email_diagnostics --to you@example.com --send
```

Production should report the SMTP backend rather than Django's console backend.
The command deliberately does not print the SMTP password. It also reports pending/failed newsletter jobs and warns when the oldest queued job has been waiting more than 15 minutes.

## 4. Newsletter queue

Publishing content now creates durable database jobs. Run this command from cron:

```bash
python manage.py process_newsletter_queue --limit 50
```

A five-minute cPanel cron is a reasonable starting point. The command recovers
stale processing jobs and retries failed recipients without re-sending recipients
already marked sent.

If the project still uses the daily digest command, schedule it separately; the
content-announcement queue and daily digest serve different purposes.


## 4A. Marketing campaign engine

ChuoSmart marketing campaigns are separate from transactional email and from the
content-announcement newsletter queue. Create campaigns in Django admin under
**Marketing campaigns**. Use **Send a test ... to my admin email** first, then
either schedule the campaign or select **Queue selected campaign(s) for sending**.

The engine only materializes opted-in recipients, deduplicates email addresses,
re-checks consent immediately before each send, honors the suppression list and
a per-campaign frequency cap, and stores one durable delivery row per recipient.
It supports pause/resume/cancel, exponential retry, stale-worker recovery and
halts immediately on SMTP authentication failure so a bad credential cannot burn
through thousands of attempts.

Run this command every minute from cPanel cron:

```bash
python manage.py process_marketing_queue --limit 10
```

For roughly 6,000 contacts, start conservatively (the default is 10 messages per
worker run) and set `MARKETING_EMAIL_MAX_PER_RUN` from the SMTP provider's
documented hourly/daily sending limit. Increase only after confirming the provider
is accepting the traffic without throttling.

Suggested production variables:

```text
MARKETING_EMAIL_MAX_PER_RUN=10
MARKETING_EMAIL_RETRY_BASE_MINUTES=10
MARKETING_EMAIL_STALE_MINUTES=30
```

Never use the marketing engine for password resets, payment messages, or job
application notifications. Those remain transactional and should send immediately.

Before sending a large campaign, verify the sending domain has valid SPF, DKIM and
DMARC records and confirm the SMTP provider's hourly/daily limit. The engine uses
Django's email backend abstraction, so you can later move bulk mail to a dedicated
provider without changing campaign/audience logic. Keep `MARKETING_REPLY_TO` on a
monitored address and set `MARKETING_BUSINESS_ADDRESS` to the business contact
address you want displayed in marketing footers.

## 5. Payment verification

Snippe webhook deliveries must be configured to the project's
`/lms/payments/snippe/webhook/` route. The webhook secret in Snippe and
`SNIPPE_WEBHOOK_SECRET` must match.

After deployment test one inexpensive module/course transaction and verify:

1. a local pending payment exists before redirect to Snippe;
2. the webhook updates that exact payment via metadata `payment_id`;
3. the paid amount and currency match the expected local amount/TZS;
4. module access or course enrollment is granted once;
5. replaying the same webhook does not grant access twice.

## 6. Private payment proofs

Payment proof files now use storage outside `MEDIA_ROOT`. Ensure your web server
cannot directly expose `PRIVATE_MEDIA_ROOT`. Access is served only through the
permission-checked Django view.

Run the migration command before deleting old public copies.

## 7. Repository data cleanup

Database dumps, SQLite databases and payment-proof uploads must not live in Git.
The normal application patches intentionally do not embed deletions of SQL dumps,
because doing so would copy sensitive data into patch files.

Use the separate `sanitize_git_history.sh` included in the downloadable patch
bundle after making an out-of-repository backup. Rewriting history changes commit
IDs and requires a coordinated force-push.

## 8. Rollback

If patches were applied with `git am` and the application has not been deployed:

```bash
git am --abort   # only while an apply is in progress
```

After commits have been applied, revert them in reverse order rather than deleting
production data:

```bash
git revert <newest-commit> ... <oldest-commit>
```

Database migrations should only be reversed after reviewing whether production
data was written into the new tables/fields.


## 9. Employer/job smoke test

After migration, verify the complete revenue-critical path with two test accounts:

1. employer creates a company;
2. employer submits verification documents;
3. staff approves the verification request in Django admin;
4. employer creates a job and confirms its visibility says Public;
5. student can open and apply to the job;
6. employer can open the applications page and the applicant detail;
7. changing application status sends a transactional email (check `logs/email.log` if delivery fails);
8. the student dashboard Career tab shows saved jobs, applications, and recommendations.

Do not deploy a jobs release based only on a successful job-row insert. The public listing, application route, employer review page, and notification path must all work together.

## Marketing/content email orchestration

ChuoSmart's content email path is deliberately two-stage. `process_newsletter_queue`
reconciles published database content and turns only the newest due content item into
a marketing campaign. `process_marketing_queue` then sends that campaign to opted-in
recipients using durable rows, suppression checks, retry backoff and global rate caps.
Publishing a blog/job/course/product/material never sends thousands of emails inside
the HTTP request.

One-time after deployment/backfill:

```bash
python manage.py sync_marketing_content_queue --preview 30
```

This scans the real database and creates missing content queue rows newest-first.
Previously processed content is not reset or resent. Expired/private jobs and inactive
materials are excluded. Course lessons are intentionally excluded by default because
broadcasting every lesson is too noisy; set `CONTENT_MARKETING_INCLUDE_COURSE_CONTENT=true`
only if that behavior is explicitly wanted.

Recommended cron jobs (every minute):

```bash
python manage.py process_newsletter_queue --limit 1
python manage.py process_marketing_queue --limit 10
```

The marketing worker still enforces `MARKETING_EMAIL_BURST_CAP`, rolling ten-minute,
hourly and daily caps even if a larger CLI `--limit` is supplied. Automatic content
campaigns are serialized, and recipients are re-checked for consent, suppression and
frequency caps immediately before SMTP delivery.

Start conservatively. The supplied production defaults are intentionally a warm-up
profile rather than a maximum-throughput profile. Increase them only after confirming
the SMTP provider quota and reviewing domain reputation/complaints.

### Recovering a failed `0034_marketing_engine` on MariaDB

If the first Patch 7 migration failed with MariaDB error 1071 (`Specified key was too
long`) before Django recorded the migration as applied, Patch 8 removes the unnecessary
wide email+timestamp index. Repair the partial tables before rerunning migrate:

```bash
python manage.py repair_marketing_migration
python manage.py migrate
```

The repair command refuses to drop tables containing rows unless `--force` is supplied.
Do not use `--force` unless you have inspected that data and know it is disposable.
