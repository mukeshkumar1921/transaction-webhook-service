from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest
pytest.importorskip("psycopg", reason="PostgreSQL driver required for API/worker tests")

from app.main import app
from worker.processor import process_transaction

PAYLOAD = {
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR",
}


def test_health_check():
    with patch("app.main.init_db"):
        with TestClient(app) as client:
            response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"
    assert response.json()["current_time"].endswith("Z")


def test_webhook_returns_202_after_persist():
    session = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = session
    with patch("app.main.SessionLocal.begin", return_value=context):
        with patch("app.main.init_db"):
            with TestClient(app) as client:
                response = client.post("/v1/webhooks/transactions", json=PAYLOAD)
    assert response.status_code == 202
    assert response.json()["transaction_id"] == PAYLOAD["transaction_id"]
    session.execute.assert_called_once()


def test_invalid_webhook_returns_422():
    with patch("app.main.init_db"):
        with TestClient(app) as client:
            response = client.post("/v1/webhooks/transactions", json={**PAYLOAD, "amount": -5})
    assert response.status_code == 422


def test_worker_marks_transaction_processed_after_delay():
    transaction = SimpleNamespace(status="PROCESSING", processed_at=None, claimed_until=datetime.now(timezone.utc))
    session = MagicMock()
    session.get.return_value = transaction
    context = MagicMock()
    context.__enter__.return_value = session
    with patch("worker.processor.SessionLocal.begin", return_value=context):
        with patch("worker.processor.time.sleep") as sleep:
            process_transaction("txn_abc123def456")
    sleep.assert_called_once_with(30)
    assert transaction.status == "PROCESSED"
    assert transaction.processed_at is not None
    assert transaction.claimed_until is None
