import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/transactions")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1"))
PROCESSING_SECONDS = int(os.environ.get("PROCESSING_SECONDS", "30"))
LEASE_SECONDS = int(os.environ.get("LEASE_SECONDS", "90"))
