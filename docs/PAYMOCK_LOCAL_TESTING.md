# ChuoMarket + PayMock local payment testing

This setup exercises the same Snippe session, redirect, signed webhook, and local payment-record logic used by ChuoMarket, but PayMock never moves real money.

## 1. Start PayMock

From the PayMock project:

```bash
docker compose up --build
```

Verify it:

```bash
curl http://127.0.0.1:8787/health
```

Expected response:

```json
{"status":"ok"}
```

## 2. Configure ChuoMarket

Copy the values from `env.paymock.example` into the environment used by Django.

When Django runs directly on your host and PayMock runs in Docker, keep:

```env
SNIPPE_BASE_URL=http://127.0.0.1:8787
SNIPPE_WEBHOOK_BASE_URL=http://host.docker.internal:8000
SNIPPE_API_KEY=snp_test_paymock_full_access
SNIPPE_WEBHOOK_SECRET=whsec_paymock_local_only
SNIPPE_ALLOWED_METHODS=mobile_money
```

When both Django and PayMock run directly on the host, change the webhook base to:

```env
SNIPPE_WEBHOOK_BASE_URL=http://127.0.0.1:8000
```

Restart Django after changing environment variables.

If PayMock runs in Docker and Django runs on the host, start Django so the Docker host gateway can reach it:

```bash
python manage.py runserver 0.0.0.0:8000
```

If PayMock runs natively on the same host, the normal `python manage.py runserver` command is enough.

## 3. Test a payment

1. Open ChuoMarket on `http://127.0.0.1:8000` or `http://localhost:8000`.
2. Start a course, module, or certificate payment.
3. ChuoMarket creates its normal local pending payment record and redirects to PayMock.
4. On the PayMock checkout page, click **Simulate successful payment** or **Simulate failed payment**.
5. PayMock creates the simulated payment event and posts a signed webhook back to ChuoMarket.
6. On success, ChuoMarket marks the matching payment completed and applies the normal access/enrollment logic.

Webhook delivery is asynchronous, so the ChuoMarket confirmation page may show pending briefly before it updates.

## 4. Useful PayMock checks

```bash
curl http://127.0.0.1:8787/__paymock/events
curl http://127.0.0.1:8787/__paymock/webhook-deliveries
```

To reset all simulated payment state:

```bash
curl -X POST http://127.0.0.1:8787/__paymock/reset
```

These admin endpoints are local development controls only.

## Production switch

For real Snippe, remove the PayMock overrides or use:

```env
SNIPPE_BASE_URL=https://api.snippe.sh
SNIPPE_ALLOWED_METHODS=mobile_money,card
SNIPPE_WEBHOOK_BASE_URL=
```

Keep the real Snippe API key and webhook secret only in your production environment.
