"""
Add ResellerXpress provider-tracking columns to orders table (Phase 2 automation).

Run once from project root:
  python scripts/add_order_provider_fields.py

Note: the new provider_webhook_events table is created automatically on app
startup (Base.metadata.create_all), so it needs no migration here.
"""

import os
import sys

# Run from project root so app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text

from app.database import engine

# column name -> type clause
COLUMNS = {
    "provider_order_id": "INTEGER NULL",
    "provider_amount": "DOUBLE PRECISION NULL",
    "provider_status": "VARCHAR NULL",
    "failure_reason": "VARCHAR NULL",
    "retry_count": "INTEGER NOT NULL DEFAULT 0",
}


def main():
    url = os.getenv("DATABASE_URL", "")
    is_pg = "postgresql" in url.lower()

    with engine.connect() as conn:
        for name, type_clause in COLUMNS.items():
            # SQLite uses INTEGER for floats fine; swap PG-only type for portability.
            clause = type_clause if is_pg else type_clause.replace("DOUBLE PRECISION", "REAL")
            stmt = f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {name} {clause}"
            if is_pg:
                conn.execute(text(stmt))
            else:
                try:
                    conn.execute(text(stmt.replace("IF NOT EXISTS ", "")))
                except Exception as e:
                    if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                        raise
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_provider_order_id ON orders (provider_order_id)"))
        conn.commit()

    print("Added provider-tracking columns to orders (or they already existed).")


if __name__ == "__main__":
    main()
