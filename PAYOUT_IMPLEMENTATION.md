# ChuoSmart — guarded Snippe instructor payouts

**Deployment safety: LIVE TRANSFERS ARE DISABLED BY DEFAULT.** This patch adds real Snippe payout execution and signed webhook reconciliation, but does **not** authorize a production transfer merely by being deployed. Complete the checklist and stage tests before setting the enable flag.

## Overview

1. The existing instructor flow creates a request for eligible earnings at **TZS 100,000 minimum**, selecting distinct earning rows up to the configured per-transfer cap and reserving them in the database. Excess earnings remain available for later requests.
2. Admin A reviews the request and selects **Approve**. Approval alone never calls Snippe.
3. Independent superuser Admin B verifies account ownership **out of band** (not merely by clicking) and selects **Authorize**. The server snapshots and encrypts recipient details, validates signed payment evidence, applies a settlement hold, validates the instructor ledger, and creates one immutable payout transfer with a permanent local idempotency key. The two administrators must have separate accounts.
4. An authorized operator invokes `python manage.py dispatch_instructor_payout --payout-id ID --execute`. With the feature flag enabled, a backend-only, restricted Snippe payout key gets the fee quote, then makes one single outbound `POST /v1/payouts/send`. The transfer is marked `sending` durably **before** this POST. An ambiguous response or timeout becomes `unknown` and is **never automatically sent again**.
5. Snippe's signed `payout.completed`, `payout.failed`, or `payout.reversed` webhook goes to `https://YOUR-DOMAIN/payouts/webhooks/snippe/`. The webhook handler verifies the raw HMAC and timestamp, deduplicates events, **GETs the provider's authoritative payout status** and cross-checks the reference, integer TZS amount and recipient. Only a confirmed `completed` turns the legacy payout status into `paid`; confirmed `failed` releases reserved entries once. Reversals keep earnings locked for manual resolution.
6. Schedule `python manage.py reconcile_instructor_payouts` periodically (e.g., every few minutes) for pending transfers, so webhooks do not become a single point of failure. `unknown` without a reference requires manual provider-ledger reconciliation and **must not** be retried.

## Settings (environment variables)

| Variable | Meaning |
|---|---|
| `INSTRUCTOR_DISBURSEMENTS_ENABLED` | Default `false`. Set `true` **only after** production launch approval and all safety checks. |
| `SNIPPE_PAYOUT_API_KEY` | Separate, narrowly scoped payout credential, **not** the existing customer collections key. |
| `SNIPPE_PAYOUT_BASE_URL` | Defaults to `https://api.snippe.sh`; host is pinned for safety. |
| `SNIPPE_WEBHOOK_SECRET` | Snippe dashboard signing secret for verifying both payment and payout webhooks. |
| `SNIPPE_PAYOUT_WEBHOOK_URL` | Public **HTTPS** URL, e.g. `https://example.com/payouts/webhooks/snippe/`. |
| `SNIPPE_PAYOUT_ENCRYPTION_KEY` | Persistent Fernet key used to encrypt payout destinations. Generate securely with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Protect and back it up; losing it prevents reconciliation. |
| `INSTRUCTOR_PAYOUT_SETTLEMENT_DAYS` | Default `7`: minimum age of earnings at authorization and again at send. |
| `INSTRUCTOR_PAYOUT_MAX_SINGLE_TZS` | Default `500000`: per-transaction cap. |
| `INSTRUCTOR_PAYOUT_MAX_DAILY_TZS` | Default `1000000`: rolling 24-hour cap with shared DB lock. |
| `INSTRUCTOR_PAYOUT_THRESHOLD_TZS` | Existing minimum, default `100000`. |

Fees are quoted and charged by Snippe from the platform provider balance **in addition** to the instructor payout amount. Ensure appropriate reserves for fees. This implementation does not deduct provider fees from instructor entitlements.

## Deploy and verify

From an unchanged project checkout, apply **either** the payout-only patch (if the share patch was already applied) **or** the combined payout-and-sharing patch (if neither feature was installed), but **not both**.

```bash
# Check, then apply chosen patch
 git apply --check chuo-market-secure-payout.patch
 git apply chuo-market-secure-payout.patch

# Apply new payout app migration while disbursements are still disabled
 python manage.py migrate
 python manage.py check
 python manage.py test payouts.tests lms.test_instructor_revenue --settings=Commerce.test_settings
 python tests/payout-source-smoke.py

# If you applied the combined patch, also run
 python manage.py test core.test_social_sharing --settings=Commerce.test_settings
 node --test tests/social-share.test.cjs
```

Before enabling live transfers:

- Verify the database migration on staging with a backup and restore tested. The project uses an **unmigrated legacy LMS app**; the new `payouts` app has an independent first migration and references old payout IDs rather than adding migrations to existing production tables. Confirm test database and production DB schema match expected types.
- Verify with the **real Snippe environment and account** that the payout key supports `/v1/payouts/*`, fee quote amounts and the response `recipient`/`reference` fields exactly as documented. Test the webhook signature with the exact Snippe dashboard secret, and configure the payout webhook URL in the Snippe dashboard or per request.
- Confirm an operational reserve for pending refunds, chargebacks, fee costs and disputes. The app currently does not have a complete financial refund/chargeback ledger. Earnings are restricted to payments with matching **processed signed Snippe customer-payment webhook receipts** and a configurable 7-day hold, but this does not replace accounting reconciliation for disputes or post-settlement reversals. Establish and enforce this operational check before sending real money.
- Create two separate privileged admin accounts. Conduct out-of-band beneficiary verification before authorizing. Approved and authorized transfers cannot be manually marked paid or rejected.
- Confirm `select_for_update` uses a database engine with row-level transactional locking, such as PostgreSQL or MySQL/InnoDB (SQLite cannot validate concurrency safety). Run multi-worker adversarial tests against the staging production-like DB.
- Check provider transaction and daily limits. Provision alerts for stuck `sending`, `unknown`, `reversed`, webhook error and insufficient balance. Retain immutable payout logs.
- Start with a tightly controlled production pilot using a single low-risk legitimate instructor transfer. Authorize only a request with verified revenue above the TZS 100,000 minimum. Check provider account statements and both the application and instructor confirmation before broad rollout.

## Provider uncertainty / incident response

A transfer in `sending` or `unknown` with no provider reference **cannot** be safely retried automatically even after Snippe's idempotency cache expires (24 hours). Inspect the provider account payout list / dashboard using the transfer idempotency key, beneficiary, amount and time. Resolve manually; do not create a new payout while the result is uncertain. Use the global disable switch to stop all new transfers immediately.

## Current coverage limits

The generated patch's Python files compile and the sharing JavaScript tests pass in the preparation environment. **Full Django test execution and a real sandbox disbursement have not been completed** because Django and its dependencies cannot be downloaded from the execution environment. Do **not** switch on live disbursements until the Django suite, concurrency tests and provider end-to-end dry runs succeed. Independent production security review is recommended.
