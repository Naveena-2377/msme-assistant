"""
Drafting endpoints (Dev Step 10). Every route here returns a draft
string for the owner to review and send themselves — none of these
send an email, WhatsApp message, or any external communication.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, Customer, Supplier
from app.schemas.drafts import CollectionsReminderRequest, VendorEmailRequest, ParseOrderRequest, DraftResponse
from app.llm.drafting import draft_collections_reminder, draft_vendor_email, parse_order_message

router = APIRouter()


@router.post("/collections-reminder", response_model=DraftResponse)
def create_collections_reminder(request: CollectionsReminderRequest, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == request.invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    customer = db.query(Customer).filter(Customer.customer_id == invoice.customer_id).first()

    days_overdue = (date.today() - invoice.due_date).days
    days_overdue = max(days_overdue, 0)

    try:
        draft = draft_collections_reminder(
            customer_name=customer.name if customer else "Customer",
            amount=invoice.amount,
            days_overdue=days_overdue,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return DraftResponse(draft_text=draft)


@router.post("/vendor-email", response_model=DraftResponse)
def create_vendor_email(request: VendorEmailRequest, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == request.supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    try:
        draft = draft_vendor_email(supplier_name=supplier.name, context=request.context)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return DraftResponse(draft_text=draft)


@router.post("/parse-order")
def create_order_parse(request: ParseOrderRequest):
    """
    Parses a free-form WhatsApp-style order message into structured
    items (product name + quantity guesses). This is a parsing aid
    only — nothing gets written to the database here. The owner is
    expected to review the parsed items and match them to real
    products themselves before proposing an actual reorder or sale.
    """
    try:
        parsed = parse_order_message(request.raw_text)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=502, detail="Could not parse the model's response as valid JSON.")

    return parsed
