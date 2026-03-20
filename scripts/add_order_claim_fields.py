"""
Add manual fulfillment claim columns to orders table.

Run once from project root:
  python scripts/add_order_claim_fields.py
"""

import os
import sys

# Run from project root so app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text

from app.database import engine


def main():
    url = os.getenv("DATABASE_URL", "")
    # Works for PostgreSQL and other SQLAlchemy-supported engines.
    # For PostgreSQL, we can use IF NOT EXISTS.
    add_claimed_by = "ALTER TABLE orders ADD COLUMN IF NOT EXISTS claimed_by VARCHAR NULL"
    add_claimed_at = "ALTER TABLE orders ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE NULL"

    with engine.connect() as conn:
        if "postgresql" in url.lower():
            conn.execute(text(add_claimed_by))
            conn.execute(text(add_claimed_at))
            conn.commit()
        else:
            # Generic fallback: try and ignore "already exists" errors.
            try:
                conn.execute(text(add_claimed_by.replace("IF NOT EXISTS ", "")))
                conn.commit()
            except Exception as e:
                if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise
            try:
                conn.execute(text(add_claimed_at.replace("IF NOT EXISTS ", "")))
                conn.commit()
            except Exception as e:
                if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise

    print("Added claim columns to orders (or they already existed).")


if __name__ == "__main__":
    main()

