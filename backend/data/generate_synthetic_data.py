"""
Synthetic data generator for MSME Assistant.

Per project spec: use synthetic/generated data only, and state this
explicitly in documentation (see docs/architecture.md).

Run from backend/:
    python data/generate_synthetic_data.py

Generates, in dependency order:
1. products      - static reference data, realistic costs/prices
2. suppliers     - static reference data
3. customers     - static reference data, each assigned a hidden
                    payment-behavior type (on_time / slight_delay /
                    chronic_late) that drives the invoices generator
4. sales_history  - base daily demand + seasonality (festival months)
                    + Poisson noise, per product, over ~2 years
5. invoices       - B2B orders drawn from customers, with payment
                    delay patterns injected per customer's behavior
                    type — this is the real signal the payment-delay
                    model will learn to predict
6. cash_ledger    - running cash balance built from sales inflows,
                    invoice payments received, and periodic reorder
                    purchases

Writes directly into data/twinops.db via the SQLAlchemy models in
app/models/, so it's usable by app/main.py and the ML layer as-is.
"""

import random
from datetime import date, timedelta

import numpy as np
from faker import Faker

from app.database import Base, engine, SessionLocal
from app.models import Product, Supplier, Customer, SalesHistory, Invoice, CashLedger

fake = Faker("en_IN")
random.seed(42)
np.random.seed(42)

TODAY = date.today()
HISTORY_DAYS = 730  # ~2 years of sales history

# A small MSME-style hardware/general-trading catalog.
PRODUCT_CATALOG = [
    ("PVC Pipe 1in", 120, 180), ("PVC Pipe 2in", 210, 300),
    ("Cement Bag 50kg", 320, 380), ("Steel Rod 12mm", 480, 560),
    ("Paint Bucket 10L", 850, 1100), ("Wire Roll 90m", 950, 1250),
    ("Tile Adhesive 20kg", 400, 480), ("Hand Drill", 1200, 1600),
    ("LED Bulb 9W", 60, 110), ("Ceiling Fan", 1400, 1900),
    ("Water Tank 500L", 3200, 4100), ("PVC Fittings Set", 90, 150),
    ("Switch Board", 140, 220), ("Nail Box 1kg", 80, 130),
    ("Plywood Sheet", 900, 1200), ("Door Hinge Set", 60, 100),
    ("Tile Grout 5kg", 180, 250), ("Adhesive Tape Roll", 25, 50),
    ("Extension Board", 220, 320), ("Safety Gloves Pair", 40, 70),
]

# Festival/demand-spike months (0-indexed: Oct=9, Nov=10 for Diwali season, etc.)
SEASONAL_BOOST_MONTHS = {3, 4, 9, 10}  # Apr, May (construction season), Oct, Nov (Diwali)

# Customer payment-behavior distribution, matches the pattern the
# payment-delay model needs to learn.
PAYMENT_BEHAVIORS = (
    ["on_time"] * 70 + ["slight_delay"] * 20 + ["chronic_late"] * 10
)


def generate_products(n=20, supplier_ids=None):
    products = []
    supplier_ids = supplier_ids or [None]
    for i, (name, cost, price) in enumerate(PRODUCT_CATALOG[:n], start=1):
        products.append(Product(
            product_id=i,
            name=name,
            current_stock=random.randint(20, 200),
            reorder_threshold=random.randint(15, 40),
            unit_cost=cost,
            unit_price=price,
            supplier_id=random.choice(supplier_ids),
        ))
    return products


def generate_suppliers(n=8):
    suppliers = []
    for i in range(1, n + 1):
        suppliers.append(Supplier(
            supplier_id=i,
            name=fake.company(),
            avg_delivery_days=round(random.uniform(2, 12), 1),
            reliability_score=round(random.uniform(0.6, 0.99), 2),
        ))
    return suppliers


def generate_customers(n=50):
    customers = []
    behaviors = {}
    for i in range(1, n + 1):
        behavior = random.choice(PAYMENT_BEHAVIORS)
        behaviors[i] = behavior
        customers.append(Customer(
            customer_id=i,
            name=fake.company(),
            avg_past_delay_days=0.0,  # filled in after invoices are generated
        ))
    return customers, behaviors


def generate_sales_history(products):
    """Base demand + seasonality + Poisson noise, per product, per day."""
    rows = []
    sale_id = 1
    start_date = TODAY - timedelta(days=HISTORY_DAYS)

    for product in products:
        # Cheaper/faster-moving items sell more units per day.
        base_demand = max(1, round(2000 / product.unit_price))

        for d in range(HISTORY_DAYS):
            current_date = start_date + timedelta(days=d)
            seasonal_factor = 1.6 if current_date.month in SEASONAL_BOOST_MONTHS else 1.0
            # Weekends slightly slower for a B2B hardware trade.
            weekday_factor = 0.7 if current_date.weekday() in (5, 6) else 1.0

            lam = base_demand * seasonal_factor * weekday_factor
            quantity = np.random.poisson(lam=max(lam, 0.1))

            if quantity > 0:
                rows.append(SalesHistory(
                    sale_id=sale_id,
                    product_id=product.product_id,
                    sale_date=current_date,
                    quantity_sold=int(quantity),
                ))
                sale_id += 1

    return rows


def generate_invoices(customers, behaviors, products, n_invoices=400):
    """
    B2B orders with payment-delay patterns injected per customer
    behavior. Uses noisy (overlapping) base distributions per behavior
    group plus two realistic interaction effects — larger invoices
    tend to get delayed more, and certain months are cash-crunch
    months — so the pattern isn't perfectly separable by a single
    threshold rule. This mirrors real MSME payment behavior, which is
    messier than "each customer always pays exactly N days late".
    """
    invoices = []
    start_date = TODAY - timedelta(days=HISTORY_DAYS)

    # Base delay distribution per behavior: (mean_days, std_days).
    # Std is wide enough relative to the gap between means that the
    # groups genuinely overlap at the tails.
    BEHAVIOR_DELAY_PARAMS = {
        "on_time": (-3.0, 3.0),
        "slight_delay": (7.0, 5.0),
        "chronic_late": (25.0, 8.0),
    }

    # Cash-crunch months: businesses stretch payables to protect their
    # own cash before Diwali stocking season.
    CASH_CRUNCH_MONTHS = {8, 9}

    for invoice_id in range(1, n_invoices + 1):
        customer = random.choice(customers)
        behavior = behaviors[customer.customer_id]

        issue_date = start_date + timedelta(days=random.randint(0, HISTORY_DAYS))
        due_date = issue_date + timedelta(days=30)
        amount = round(random.uniform(3000, 60000), 2)

        # Base noisy delay from the customer's behavior group (overlapping).
        mean_delay, std_delay = BEHAVIOR_DELAY_PARAMS[behavior]
        base_delay = np.random.normal(mean_delay, std_delay)

        # Larger invoices get delayed more (up to +4 days at the top end).
        amount_effect = (amount / 60000) * 4

        # Cash-crunch season adds a delay bump regardless of behavior type.
        seasonal_effect = 3.0 if issue_date.month in CASH_CRUNCH_MONTHS else 0.0

        delay_days = int(round(base_delay + amount_effect + seasonal_effect))
        delay_days = max(delay_days, -5)  # nobody pays more than 5 days early

        paid_date = due_date + timedelta(days=delay_days)

        if paid_date > TODAY:
            # Hasn't actually been paid yet as of "today".
            paid_date_val = None
            status = "overdue" if due_date < TODAY else "pending"
        else:
            paid_date_val = paid_date
            status = "paid"

        invoices.append(Invoice(
            invoice_id=invoice_id,
            customer_id=customer.customer_id,
            amount=amount,
            issue_date=issue_date,
            due_date=due_date,
            paid_date=paid_date_val,
            status=status,
        ))

    return invoices


def backfill_customer_avg_delay(customers, invoices):
    """Compute avg_past_delay_days per customer from their paid invoices."""
    by_customer = {}
    for inv in invoices:
        if inv.paid_date is not None:
            delay = (inv.paid_date - inv.due_date).days
            by_customer.setdefault(inv.customer_id, []).append(delay)

    for customer in customers:
        delays = by_customer.get(customer.customer_id, [])
        customer.avg_past_delay_days = round(float(np.mean(delays)), 1) if delays else 0.0

    return customers


def generate_cash_ledger(sales_history, invoices, products):
    """Running cash balance from sales inflows, invoice payments, and reorder purchases."""
    price_by_product = {p.product_id: p.unit_price for p in products}
    cost_by_product = {p.product_id: p.unit_cost for p in products}

    events = []  # (date, type, amount)

    for sale in sales_history:
        revenue = sale.quantity_sold * price_by_product[sale.product_id]
        events.append((sale.sale_date, "sale", revenue))

    for inv in invoices:
        if inv.paid_date is not None:
            events.append((inv.paid_date, "payment_received", inv.amount))

    # Simplified periodic reorder purchases: every ~10 days, restock at cost.
    start_date = TODAY - timedelta(days=HISTORY_DAYS)
    for d in range(0, HISTORY_DAYS, 10):
        purchase_date = start_date + timedelta(days=d)
        product = random.choice(products)
        qty = random.randint(30, 100)
        cost = qty * cost_by_product[product.product_id]
        events.append((purchase_date, "purchase", -cost))

    events.sort(key=lambda e: e[0])

    ledger = []
    balance = 50000.0  # starting cash float for a small MSME
    for i, (event_date, event_type, amount) in enumerate(events, start=1):
        balance += amount
        ledger.append(CashLedger(
            entry_id=i,
            date=event_date,
            transaction_type=event_type,
            amount=round(amount, 2),
            running_balance=round(balance, 2),
        ))

    return ledger


def main():
    print("Creating tables (if not already present)...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Clearing any existing rows...")
        for model in (CashLedger, Invoice, SalesHistory, Customer, Product, Supplier):
            db.query(model).delete()
        db.commit()

        print("Generating suppliers...")
        suppliers = generate_suppliers()
        db.add_all(suppliers)
        db.commit()

        print("Generating products...")
        products = generate_products(supplier_ids=[s.supplier_id for s in suppliers])
        db.add_all(products)
        db.commit()

        print("Generating customers...")
        customers, behaviors = generate_customers()
        db.add_all(customers)
        db.commit()

        print("Generating sales history (this is the slow one)...")
        sales_history = generate_sales_history(products)
        db.add_all(sales_history)
        db.commit()

        print("Generating invoices...")
        invoices = generate_invoices(customers, behaviors, products)
        db.add_all(invoices)
        db.commit()

        print("Backfilling customer avg payment delay...")
        customers = backfill_customer_avg_delay(customers, invoices)
        db.commit()

        print("Generating cash ledger...")
        ledger = generate_cash_ledger(sales_history, invoices, products)
        db.add_all(ledger)
        db.commit()

        print(f"Done. {len(products)} products, {len(suppliers)} suppliers, "
              f"{len(customers)} customers, {len(sales_history)} sales rows, "
              f"{len(invoices)} invoices, {len(ledger)} ledger entries.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
