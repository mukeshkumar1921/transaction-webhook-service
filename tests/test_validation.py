from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.schemas import WebhookPayload


def test_valid_payload_normalizes_currency():
    payload = WebhookPayload(transaction_id="txn_1", source_account="a", destination_account="b", amount="150.50", currency="inr")
    assert payload.currency == "INR"
    assert payload.amount == Decimal("150.50")


@pytest.mark.parametrize("amount", [0, -1, "not-a-number"])
def test_invalid_amount(amount):
    with pytest.raises(ValidationError):
        WebhookPayload(transaction_id="txn_1", source_account="a", destination_account="b", amount=amount, currency="INR")
