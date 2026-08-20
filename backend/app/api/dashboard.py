"""
Dashboard endpoint — a single-glance summary of business health,
pulling from products, invoices, decisions, and cash ledger. This is
usually the first thing a real owner would want to see when opening
the app, rather than starting on any one specific page.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Invoice, Decision
from app.twin.simulate import get_current_cash_balance, estimate_daily_demand, stockout_risk_label

router = APIRouter()


@router.get("/")
def get_dashboard(db: Session = Depends(get_db)):
    current_cash = get_current_cash_balance(db)

    products = db.query(Product).all()
    below_threshold_count = sum(1 for p in products if p.current_stock < p.reorder_threshold)

    high_risk_count = 0
    for p in products:
        daily_demand = estimate_daily_demand(db, p.product_id)
        days_of_stock = (p.current_stock / daily_demand) if daily_demand > 0 else None
        if days_of_stock is not None and stockout_risk_label(days_of_stock) == "high":
            high_risk_count += 1

    unpaid_invoices = db.query(Invoice).filter(Invoice.paid_date.is_(None)).all()
    overdue_count = sum(1 for inv in unpaid_invoices if inv.status == "overdue")
    unpaid_total = round(sum(inv.amount for inv in unpaid_invoices), 2)

    pending_approvals = db.query(Decision).filter(Decision.approval_status == "pending").count()

    return {
        "current_cash": round(current_cash, 2),
        "total_products": len(products),
        "products_below_threshold": below_threshold_count,
        "products_high_risk": high_risk_count,
        "unpaid_invoices_count": len(unpaid_invoices),
        "overdue_invoices_count": overdue_count,
        "unpaid_invoices_total": unpaid_total,
        "pending_approvals": pending_approvals,
    }
