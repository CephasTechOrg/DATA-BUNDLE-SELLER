"""Add payment_reference_phone column to orders table. Run once from project root: python scripts/add_payment_reference_phone_column.py"""
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
    with engine.connect() as conn:
        if "postgresql" in url.lower():
            conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_reference_phone VARCHAR NULL"))
            conn.commit()
            print("PostgreSQL: added column payment_reference_phone (or it already existed).")
        else:
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN payment_reference_phone VARCHAR NULL"))
                conn.commit()
                print("Added column payment_reference_phone.")
            except Exception as e:
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print("Column payment_reference_phone already exists.")
                else:
                    raise

if __name__ == "__main__":
    main()
