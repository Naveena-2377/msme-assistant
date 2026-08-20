"""
Invoices / Collections endpoint (Dev Step 9).

Purpose: the collections page an MSME owner would check to decide who
to chase for payment first. Ranks unpaid/overdue invoices by risk,
using each customer's historical average payment delay (already
tracked on the Customer model) as the risk signal — the same
leakage-safe idea used in app/ml/payment_delay.py, but read directly
from stored state rather than re-running the model live.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, Customer, CashLedger
from app.twin.simulate import get_current_cash_balance

router = APIRouter()

RISK_HIGH_THRESHOLD = 15   # avg past delay > this many days -> high risk
RISK_MEDIUM_THRESHOLD = 5  # avg past delay > this many days -> medium risk


def _delay_risk_label(avg_delay_days: float) -> str:
    if avg_delay_days > RISK_HIGH_THRESHOLD:
        return "high"
    elif avg_delay_days > RISK_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


@router.get("/")
def list_unpaid_invoices(db: Session = Depends(get_db)):
    today = date.today()
    invoices = (
        db.query(Invoice)
        .filter(Invoice.paid_date.is_(None))
        .all()
    )

    results = []
    for inv in invoices:
        customer = db.query(Customer).filter(Customer.customer_id == inv.customer_id).first()
        days_overdue = (today - inv.due_date).days
        results.append({
            "invoice_id": inv.invoice_id,
            "customer_id": inv.customer_id,
            "customer_name": customer.name if customer else "Unknown",
            "amount": inv.amount,
            "issue_date": inv.issue_date,
            "due_date": inv.due_date,
            "status": inv.status,
            "days_overdue": days_overdue if days_overdue > 0 else 0,
            "customer_avg_past_delay_days": customer.avg_past_delay_days if customer else 0.0,
            "risk": _delay_risk_label(customer.avg_past_delay_days if customer else 0.0),
        })

    risk_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda r: (risk_order[r["risk"]], -r["days_overdue"]))
    return results


@router.post("/{invoice_id}/mark-paid")
def mark_invoice_paid(invoice_id: int, db: Session = Depends(get_db)):
    """
    Records that an invoice has been paid: sets paid_date/status and
    logs the payment as revenue in the cash ledger. Also updates the
    customer's avg_past_delay_days so future risk ranking reflects it.
    """
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.paid_date is not None:
        raise HTTPException(status_code=400, detail="Invoice is already marked paid")

    today = date.today()
    invoice.paid_date = today
    invoice.status = "paid"

    current_cash = get_current_cash_balance(db)
    new_balance = current_cash + invoice.amount
    last_entry = db.query(CashLedger).order_by(CashLedger.entry_id.desc()).first()
    next_id = (last_entry.entry_id + 1) if last_entry else 1
    db.add(CashLedger(
        entry_id=next_id,
        date=today,
        transaction_type="payment_received",
        amount=round(invoice.amount, 2),
        running_balance=round(new_balance, 2),
    ))

    # Recompute this customer's average delay from all their paid invoices.
    customer = db.query(Customer).filter(Customer.customer_id == invoice.customer_id).first()
    if customer:
        paid_invoices = (
            db.query(Invoice)
            .filter(Invoice.customer_id == customer.customer_id, Invoice.paid_date.isnot(None))
            .all()
        )
        delays = [(inv.paid_date - inv.due_date).days for inv in paid_invoices]
        customer.avg_past_delay_days = round(sum(delays) / len(delays), 1) if delays else 0.0

    db.commit()

    return {
        "invoice_id": invoice_id,
        "paid_date": str(today),
        "new_cash_balance": round(new_balance, 2),
    }
