"""
Simulation layer — the "digital twin" (Dev Step 5).

This is the core technical contribution of MSME Assistant. It must actually
COMPUTE a projected outcome from a proposed action, not just look up
current state — that's what separates a twin from a plain dashboard.

Currently implements: reorder simulation (the recommended starting
point per the project spec, since it directly consumes the demand
forecasting model). Other action types (collections priority, vendor
payment) follow the same pattern and can be added the same way.

Run directly for a demo of what it computes:
    python -m app.twin.simulate
(run from backend/, so `app` resolves as a package)
"""

from datetime import timedelta, date

from app.database import SessionLocal
from app.models import Product, SalesHistory, CashLedger

DEMAND_WINDOW_DAYS = 30  # recent window used to estimate daily demand


def get_current_cash_balance(db) -> float:
    """Most recent running_balance in the cash ledger."""
    latest = db.query(CashLedger).order_by(CashLedger.date.desc(), CashLedger.entry_id.desc()).first()
    return latest.running_balance if latest else 0.0


def estimate_daily_demand(db, product_id: int, window_days: int = DEMAND_WINDOW_DAYS) -> float:
    """
    Average units sold per day over the last `window_days`. This is a
    simple stand-in for calling the trained forecasting model
    (app.ml.demand_forecasting) — swap this call for a real forecast
    once that model is wired into the API.
    """
    cutoff = date.today() - timedelta(days=window_days)
    rows = (
        db.query(SalesHistory)
        .filter(SalesHistory.product_id == product_id, SalesHistory.sale_date >= cutoff)
        .all()
    )
    if not rows:
        return 0.0
    total_units = sum(r.quantity_sold for r in rows)
    return total_units / window_days


def stockout_risk_label(days_of_stock: float) -> str:
    if days_of_stock < 7:
        return "high"
    elif days_of_stock < 14:
        return "medium"
    return "low"


def simulate_reorder(db, product_id: int, quantity: int) -> dict:
    """
    Given a proposed reorder of `quantity` units for `product_id`,
    compute the projected state after that purchase: cash balance
    after paying for it, stock level after receiving it, and
    stockout-risk before vs. after based on recent demand.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise ValueError(f"No product with id {product_id}")

    current_cash = get_current_cash_balance(db)
    current_stock = product.current_stock
    purchase_cost = quantity * product.unit_cost
    projected_cash = current_cash - purchase_cost
    projected_stock = current_stock + quantity

    daily_demand = estimate_daily_demand(db, product_id)
    days_before = (current_stock / daily_demand) if daily_demand > 0 else float("inf")
    days_after = (projected_stock / daily_demand) if daily_demand > 0 else float("inf")

    return {
        "action_type": "reorder",
        "product_id": product_id,
        "product_name": product.name,
        "quantity": quantity,
        "purchase_cost": round(purchase_cost, 2),
        "current_cash": round(current_cash, 2),
        "projected_cash": round(projected_cash, 2),
        "current_stock": current_stock,
        "projected_stock": projected_stock,
        "avg_daily_demand": round(daily_demand, 2),
        "days_of_stock_before": round(days_before, 1) if days_before != float("inf") else None,
        "days_of_stock_after": round(days_after, 1) if days_after != float("inf") else None,
        "stockout_risk_before": stockout_risk_label(days_before),
        "stockout_risk_after": stockout_risk_label(days_after),
    }


def execute_reorder(db, product_id: int, quantity: int) -> dict:
    """
    Actually apply an approved reorder: increase product stock and
    record the purchase in the cash ledger. Only call this after a
    decision has been approved (auto or human) — never before the
    rule check has run.
    """
    from datetime import date as _date
    from app.models import CashLedger as _CashLedger

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise ValueError(f"No product with id {product_id}")

    cost = quantity * product.unit_cost
    current_cash = get_current_cash_balance(db)
    new_balance = current_cash - cost

    product.current_stock += quantity

    last_entry = db.query(CashLedger).order_by(CashLedger.entry_id.desc()).first()
    next_id = (last_entry.entry_id + 1) if last_entry else 1

    ledger_entry = _CashLedger(
        entry_id=next_id,
        date=_date.today(),
        transaction_type="purchase",
        amount=round(-cost, 2),
        running_balance=round(new_balance, 2),
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(product)

    return {
        "product_id": product_id,
        "new_stock": product.current_stock,
        "new_cash_balance": round(new_balance, 2),
    }


def record_sale(db, product_id: int, quantity: int, unit_price: float = None) -> dict:
    """
    Records an actual sale: decrements stock, appends to sales_history
    (so tomorrow's demand forecast sees it too), and logs the revenue
    in the cash ledger. This is the missing link between "what's
    happening in the shop" and what the twin knows — without this,
    stock only ever goes up (from reorders) and never down.
    """
    from datetime import date as _date
    from app.models import SalesHistory as _SalesHistory, CashLedger as _CashLedger

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise ValueError(f"No product with id {product_id}")
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if product.current_stock < quantity:
        raise ValueError(
            f"Cannot sell {quantity} units — only {product.current_stock} in stock"
        )

    price = unit_price if unit_price is not None else product.unit_price
    revenue = quantity * price

    product.current_stock -= quantity

    last_sale = db.query(_SalesHistory).order_by(_SalesHistory.sale_id.desc()).first()
    next_sale_id = (last_sale.sale_id + 1) if last_sale else 1
    db.add(_SalesHistory(
        sale_id=next_sale_id,
        product_id=product_id,
        sale_date=_date.today(),
        quantity_sold=quantity,
    ))

    current_cash = get_current_cash_balance(db)
    new_balance = current_cash + revenue
    last_entry = db.query(CashLedger).order_by(CashLedger.entry_id.desc()).first()
    next_entry_id = (last_entry.entry_id + 1) if last_entry else 1
    db.add(_CashLedger(
        entry_id=next_entry_id,
        date=_date.today(),
        transaction_type="sale",
        amount=round(revenue, 2),
        running_balance=round(new_balance, 2),
    ))

    db.commit()
    db.refresh(product)

    return {
        "product_id": product_id,
        "product_name": product.name,
        "quantity_sold": quantity,
        "unit_price": price,
        "revenue": round(revenue, 2),
        "new_stock": product.current_stock,
        "new_cash_balance": round(new_balance, 2),
    }


def adjust_stock(db, product_id: int, new_stock: int) -> dict:
    """
    Directly sets a product's stock level — for stocktaking
    corrections, damaged/lost goods, or any discrepancy between what
    the system thinks is in stock and what's physically there. Does
    NOT touch cash (no money changed hands) or sales_history (nothing
    was sold) — only current_stock.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise ValueError(f"No product with id {product_id}")
    if new_stock < 0:
        raise ValueError("Stock cannot be negative")

    old_stock = product.current_stock
    product.current_stock = new_stock
    db.commit()
    db.refresh(product)

    return {
        "product_id": product_id,
        "product_name": product.name,
        "old_stock": old_stock,
        "new_stock": new_stock,
    }


def main():
    """Demo: simulate a reorder for the first product with the lowest stock."""
    db = SessionLocal()
    try:
        product = db.query(Product).order_by(Product.current_stock.asc()).first()
        if product is None:
            print("No products found. Run the data generator first.")
            return

        print(f"Simulating a reorder for: {product.name} (id={product.product_id})")
        print(f"Current stock: {product.current_stock}, reorder threshold: {product.reorder_threshold}")

        quantity = max(product.reorder_threshold * 3, 30)
        outcome = simulate_reorder(db, product.product_id, quantity)

        print("\n=== Simulated outcome ===")
        for key, value in outcome.items():
            print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
