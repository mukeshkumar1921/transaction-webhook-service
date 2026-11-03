from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal, init_db
from app.models import Transaction
from app.schemas import TransactionResponse, WebhookPayload

app = FastAPI(title="Transaction Webhook Service", version="1.0.0")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def health():
    return {"status": "HEALTHY", "current_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}

@app.post("/v1/webhooks/transactions", status_code=status.HTTP_202_ACCEPTED)
def accept_webhook(payload: WebhookPayload):
    # A unique primary key and ON CONFLICT make concurrent deliveries idempotent.
    stmt = insert(Transaction).values(**payload.model_dump()).on_conflict_do_nothing(index_elements=["transaction_id"])
    try:
        with SessionLocal.begin() as session:
            session.execute(stmt)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Transaction could not be persisted")
    return {"message": "accepted", "transaction_id": payload.transaction_id}

@app.get("/v1/transactions/{transaction_id}", response_model=list[TransactionResponse])
def transaction_status(transaction_id: str):
    try:
        with SessionLocal() as session:
            transaction = session.scalar(select(Transaction).where(Transaction.transaction_id == transaction_id))
            if transaction is None:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return [transaction]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable")
