# ChuoSmart Marketing Engine Runbook

## What runs automatically

The marketing engine is database-backed but Django does not run background jobs by itself. Production must invoke the engine from cron.

Use one unified worker command:

```bash
python manage.py run_email_marketing_engine --send-limit 10
```

That one command:

1. discovers newly-published eligible database content;
2. keeps the durable content inventory newest-first;
3. groups due content into a useful digest instead of one email per database row;
4. prepares the current opted-in audience;
5. sends only the rate-budgeted delivery batch;
6. retries temporary/policy failures without suppressing valid users;
7. keeps confirmed nonexistent mailboxes suppressed.

## Production cron

Create the log directory once:

```bash
mkdir -p /home/chuowlwe/repositories/chuo-market3/logs
```

Then use one cron entry:

```cron
* * * * * cd /home/chuowlwe/repositories/chuo-market3 && DJANGO_ENV=production /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/python manage.py run_email_marketing_engine --send-limit 10 >> /home/chuowlwe/repositories/chuo-market3/logs/marketing_engine.log 2>&1
```

Do not run the old two marketing cron entries at the same time as the unified cron. The underlying row locks are defensive, but one cron is simpler to operate and diagnose.

## Status

```bash
python manage.py marketing_status
```

This shows opted-in audience counts, campaign states, delivery states, the active campaign, pending/retryable counts, recent delivery errors, and the next content item.

## Test the real marketing-shaped SMTP path

```bash
python manage.py marketing_test_send --to your-address@example.com
```

This sends one email with the same marketing template and unsubscribe headers as a real campaign. Use it before reopening a bulk queue after an SMTP/provider incident.

## Repair suppressions created by the older broad 5xx classifier

First preview:

```bash
python manage.py repair_marketing_suppressions
```

If the rows shown as RELEASE are policy/ambiguous rejections rather than explicit nonexistent mailboxes:

```bash
python manage.py repair_marketing_suppressions --apply
```

The command only targets active suppressions whose source is the old `smtp_hard_bounce` classifier. Explicit missing-mailbox evidence stays suppressed.

## Recommended starting settings

```env
MARKETING_EMAIL_MAX_PER_RUN=10
MARKETING_EMAIL_BURST_CAP=3
MARKETING_EMAIL_TEN_MINUTE_CAP=15
MARKETING_EMAIL_HOURLY_CAP=100
MARKETING_EMAIL_DAILY_CAP=1500
MARKETING_EMAIL_SECONDS_BETWEEN_SENDS=1
MARKETING_EMAIL_POLICY_RETRY_MINUTES=60
MARKETING_EMAIL_POLICY_FAILURE_CIRCUIT_BREAKER=3
MARKETING_SERIALIZE_CAMPAIGNS=true

CONTENT_MARKETING_DIGEST_SIZE=12
CONTENT_MARKETING_CAMPAIGN_GAP_HOURS=24
CONTENT_MARKETING_RECIPIENT_GAP_HOURS=48
CONTENT_MARKETING_RECONCILE_LIMIT=250
CONTENT_MARKETING_INCLUDE_COURSE_CONTENT=false
```

Increase throughput only after the SMTP provider/domain reputation is healthy. Recipient frequency caps and unsubscribe/suppression checks are intentionally independent from the raw SMTP rate budget.
