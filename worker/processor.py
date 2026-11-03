import logging
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from app.config import LEASE_SECONDS, POLL_INTERVAL, PROCESSING_SECONDS
from app.database import SessionLocal, init_db
from app.models import Transaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def claim_transaction():
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as session:
        transaction = session.scalar(
            select(Transaction)
            .where(Transaction.status == "PROCESSING")
            .where(or_(Transaction.claimed_until.is_(None), Transaction.claimed_until < now))
            .order_by(Transaction.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if transaction is None:
            return None
        transaction.claimed_until = now + timedelta(seconds=LEASE_SECONDS)
        transaction.attempts += 1
        return transaction.transaction_id

def process_transaction(transaction_id):
    # Simulates the external processor call without blocking the HTTP service.
    time.sleep(PROCESSING_SECONDS)
    with SessionLocal.begin() as session:
        transaction = session.get(Transaction, transaction_id, with_for_update=True)
        if transaction and transaction.status == "PROCESSING":
            transaction.status = "PROCESSED"
            transaction.processed_at = datetime.now(timezone.utc)
            transaction.claimed_until = None
            logger.info("Processed %s", transaction_id)

def run():
    if LEASE_SECONDS <= PROCESSING_SECONDS:
        raise ValueError("LEASE_SECONDS must exceed PROCESSING_SECONDS")
    init_db()
    logger.info("Worker started")
    while True:
        try:
            transaction_id = claim_transaction()
            if transaction_id:
                process_transaction(transaction_id)
            else:
                time.sleep(POLL_INTERVAL)
        except SQLAlchemyError:
            logger.exception("Database error; retrying")
            time.sleep(3)
        except Exception:
            logger.exception("Unexpected worker error; retrying")
            time.sleep(3)

if __name__ == "__main__":
    run()
