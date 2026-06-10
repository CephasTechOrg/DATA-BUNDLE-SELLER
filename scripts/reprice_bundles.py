"""
Align bundles with the ResellerXpress catalog and apply our selling margin.

Two actions:
  1. Deactivate "orphan" bundles (provider_plan_id IS NULL) — sizes ResellerXpress
     does not accept, so they must not be sellable/auto-fulfilled.
  2. Re-price every active, mapped bundle to selling = cost + tiered margin:
       - 1-5 GB   : + GH1.50 flat
       - 6-20 GB  : + 10%
       - 25 GB+   : + 7%
     Selling is rounded UP to the nearest GH0.10 so margin is never shaved.

Admins can still hand-edit any selling price afterwards in the panel.

Run from project root:
  python scripts/reprice_bundles.py            # apply changes
  python scripts/reprice_bundles.py --dry-run  # preview only
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.models import Bundle
from app.reprice import margin_price  # shared tiered-margin logic (single source of truth)


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        bundles = db.query(Bundle).order_by(Bundle.network, Bundle.capacity_mb).all()
        deactivated = repriced = 0

        print("%-12s %8s %8s %9s %9s %9s  %s" % (
            "network", "cap_mb", "plan_id", "cost", "old_sell", "new_sell", "action"))
        for b in bundles:
            if b.provider_plan_id is None:
                action = ""
                if b.is_active:
                    if not dry_run:
                        b.is_active = False
                    deactivated += 1
                    action = "DEACTIVATE (no provider plan)"
                print("%-12s %8s %8s %9.2f %9.2f %9s  %s" % (
                    b.network, b.capacity_mb, "None", b.cost_price_ghs, b.selling_price_ghs, "-", action))
                continue

            new_sell = margin_price(b.capacity_mb, float(b.cost_price_ghs))
            old_sell = float(b.selling_price_ghs)
            action = ""
            if abs(new_sell - old_sell) > 0.001:
                if not dry_run:
                    b.selling_price_ghs = new_sell
                repriced += 1
                action = "reprice (margin +%.2f)" % (new_sell - float(b.cost_price_ghs))
            print("%-12s %8s %8s %9.2f %9.2f %9.2f  %s" % (
                b.network, b.capacity_mb, b.provider_plan_id, b.cost_price_ghs, old_sell, new_sell, action))

        if not dry_run:
            db.commit()
        print("\n%s: deactivated=%s repriced=%s" % (
            "DRY-RUN (no changes saved)" if dry_run else "DONE", deactivated, repriced))
    finally:
        db.close()


if __name__ == "__main__":
    main()
