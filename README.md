# Transaction Webhook Service

A small Python service for accepting payment transaction webhooks quickly and processing them asynchronously.

## Stack

FastAPI, PostgreSQL, SQLAlchemy, and a separate database-backed Python worker. PostgreSQL is both the durable store and the worker queue, keeping the deployment small without introducing Redis/Celery for this assessment.

## Run locally (Docker Desktop)

```powershell
docker compose up --build -d
```

Open http://localhost:8000/docs for the interactive API docs.

## Try it on Windows PowerShell

```powershell
$body = @{transaction_id="txn_abc123def456"; source_account="acc_user_789"; destination_account="acc_merchant_456"; amount=1500; currency="INR"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/webhooks/transactions -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri http://localhost:8000/v1/transactions/txn_abc123def456
Start-Sleep -Seconds 32
Invoke-RestMethod -Uri http://localhost:8000/v1/transactions/txn_abc123def456
```

The webhook returns HTTP 202 after committing the row. The status endpoint returns an array (matching the assessment's example) with `PROCESSING` initially and `PROCESSED` after roughly 30 seconds. Repeating the POST with the same `transaction_id` is safe.

Stop services with `docker compose down` (data remains in the named volume).

## Design choices

- **Durability:** Commit a transaction to PostgreSQL before acknowledging it. A database outage returns 503 instead of falsely acknowledging an unpersisted transaction.
- **Idempotency:** `transaction_id` is the primary key; `INSERT ... ON CONFLICT DO NOTHING` prevents duplicate records even with concurrent requests.
- **Worker isolation:** The API never waits for the simulated 30-second operation. The independent worker polls for unclaimed rows and uses PostgreSQL `FOR UPDATE SKIP LOCKED` to prevent two workers from claiming the same row concurrently.
- **Recovery:** Claims have an expiry (90 seconds by default), so a crashed worker's transaction becomes eligible again. The final state is written durably.
- **Validation:** Pydantic rejects invalid payloads and nonpositive amounts.

## Limitations and production improvements

- The simulated processing step has no external side effect. With a real payment processor, an expired lease could cause a retry; propagate `transaction_id` as an idempotency key to the external provider to ensure effectively-once side effects.
- This worker processes one transaction at a time. Run additional worker replicas for throughput. For very long tasks, renew leases while processing.
- Webhook authentication/signature verification is not implemented because the assessment supplies no signing scheme or secret. A production integration must verify provider signatures and reject untrusted requests.
- The health endpoint reports service liveness, not database readiness.
- The 500 ms target depends on database latency and cloud cold starts; benchmark the deployed service rather than assuming a hard guarantee.

## Cloud deployment

Use a platform that supports **two continuously running services** (API and worker) and a managed PostgreSQL database. Set `DATABASE_URL` on both services. API start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Worker start command:

```bash
python -m worker.processor
```

Do not deploy only the API: without the worker, transactions will remain in `PROCESSING`. Avoid sleeping/free-tier services for the worker, since they may suspend background processing.

## API

| Method | Route | Behavior |
|---|---|---|
| GET | `/` | Liveness and UTC time |
| POST | `/v1/webhooks/transactions` | Validate, persist, return 202 |
| GET | `/v1/transactions/{transaction_id}` | Transaction details as an array; 404 if missing |

## Run unit tests

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

The included tests cover payload validation. End-to-end persistence, duplicate delivery, and worker recovery should also be verified against the running Docker Compose stack before submission.
