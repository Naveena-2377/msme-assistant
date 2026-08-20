"""
Rule / safety layer (Dev Step 6).

Purpose: check a simulated outcome (from app.twin.simulate) against
safety constraints and decide whether the action can be auto-approved,
needs human review, or should be rejected outright. This is the
visible proof of "safety-gated automation" — nothing skips this step.

Run directly for a demo across a safe, a risky, and an unsafe reorder:
    python -m app.rules.rule_engine
(run from backend/, so `app` resolves as a package)
"""

from app.database import SessionLocal
from app.twin.simulate import simulate_reorder

# --- Configurable safety constraints -----------------------------------
# These would normally come from business owner settings, not hardcoded.
MIN_CASH_FLOOR = 20000.0            # never let projected cash drop below this
MAX_PURCHASE_FRACTION = 0.5         # a single purchase can't eat more than 50% of current cash
HIGH_RISK_AFTER_NOT_ALLOWED = True  # if stock is still "high risk" after the action, flag it
# -------------------------------------------------------------------------


def check_reorder(outcome: dict) -> dict:
    """
    Given a simulated reorder outcome (dict from simulate_reorder),
    return {"result": "auto_approved" | "flagged" | "rejected", "reasons": [...]}
    """
    reasons = []

    # Hard safety violation -> reject outright.
    if outcome["projected_cash"] < MIN_CASH_FLOOR:
        reasons.append(
            f"Projected cash ({outcome['projected_cash']}) would drop below "
            f"the minimum floor ({MIN_CASH_FLOOR})."
        )
        return {"result": "rejected", "reasons": reasons}

    # High-impact purchase relative to current cash -> needs human eyes.
    if outcome["current_cash"] > 0:
        purchase_fraction = outcome["purchase_cost"] / outcome["current_cash"]
        if purchase_fraction > MAX_PURCHASE_FRACTION:
            reasons.append(
                f"Purchase cost is {purchase_fraction:.0%} of current cash, "
                f"above the {MAX_PURCHASE_FRACTION:.0%} auto-approval limit."
            )

    # Action doesn't actually fix the stockout risk -> needs review.
    if HIGH_RISK_AFTER_NOT_ALLOWED and outcome["stockout_risk_after"] == "high":
        reasons.append(
            "Stockout risk remains 'high' even after this reorder — "
            "quantity may be insufficient."
        )

    if reasons:
        return {"result": "flagged", "reasons": reasons}

    reasons.append("Within cash floor, purchase size, and stockout-risk limits.")
    return {"result": "auto_approved", "reasons": reasons}


def main():
    db = SessionLocal()
    try:
        # Case 1: the realistic case from the simulation demo (safe reorder).
        product_low_stock = None
        from app.models import Product
        product_low_stock = db.query(Product).order_by(Product.current_stock.asc()).first()

        print("=== Case 1: reasonable reorder ===")
        outcome1 = simulate_reorder(db, product_low_stock.product_id, product_low_stock.reorder_threshold * 3)
        result1 = check_reorder(outcome1)
        print(f"Product: {outcome1['product_name']}, quantity: {outcome1['quantity']}")
        print(f"Decision: {result1['result']}")
        for r in result1["reasons"]:
            print(f"  - {r}")

        # Case 2: an oversized order relative to current cash -> should be flagged/rejected.
        print("\n=== Case 2: deliberately oversized reorder ===")
        huge_quantity = 500000
        outcome2 = simulate_reorder(db, product_low_stock.product_id, huge_quantity)
        result2 = check_reorder(outcome2)
        print(f"Product: {outcome2['product_name']}, quantity: {outcome2['quantity']}")
        print(f"Projected cash: {outcome2['projected_cash']}")
        print(f"Decision: {result2['result']}")
        for r in result2["reasons"]:
            print(f"  - {r}")

        # Case 3: too small a reorder to fix the risk -> should be flagged.
        print("\n=== Case 3: reorder too small to fix stockout risk ===")
        outcome3 = simulate_reorder(db, product_low_stock.product_id, 5)
        result3 = check_reorder(outcome3)
        print(f"Product: {outcome3['product_name']}, quantity: {outcome3['quantity']}")
        print(f"Stockout risk after: {outcome3['stockout_risk_after']}")
        print(f"Decision: {result3['result']}")
        for r in result3["reasons"]:
            print(f"  - {r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
