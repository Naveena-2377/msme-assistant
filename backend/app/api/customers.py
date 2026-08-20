"""
Customers endpoint. Read-only list, used by the WhatsApp order parser
so a parsed message can be tied to a specific customer instead of
floating unattributed text.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer

router = APIRouter()


@router.get("/")
def list_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).order_by(Customer.name.asc()).all()
    return [
        {
            "customer_id": c.customer_id,
            "name": c.name,
            "avg_past_delay_days": c.avg_past_delay_days,
        }
        for c in customers
    ]
