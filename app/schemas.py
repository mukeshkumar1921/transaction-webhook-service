from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class WebhookPayload(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=100)
    source_account: str = Field(min_length=1, max_length=100)
    destination_account: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("currency must contain three letters")
        return value.upper()

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
    status: Literal["PROCESSING", "PROCESSED"]
    created_at: datetime
    processed_at: datetime | None
