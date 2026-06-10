"""
Add provider_plan_id column to bundles table (ResellerXpress plan mapping).

Run once from project root:
  python scripts/add_bundle_provider_plan_id.py
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
    add_col = "ALTER TABLE bundles ADD COLUMN IF NOT EXISTS provider_plan_id INTEGER NULL"
    add_idx = "CREATE INDEX IF NOT EXISTS ix_bundles_provider_plan_id ON bundles (provider_plan_id)"

    with engine.connect() as conn:
        if "postgresql" in url.lower():
            conn.execute(text(add_col))
            conn.execute(text(add_idx))
            conn.commit()
        else:
            # Generic fallback: try and ignore "already exists" errors.
            try:
                conn.execute(text(add_col.replace("IF NOT EXISTS ", "")))
                conn.commit()
            except Exception as e:
                if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise

    print("Added provider_plan_id column to bundles (or it already existed).")


if __name__ == "__main__":
    main()
