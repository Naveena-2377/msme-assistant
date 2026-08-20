from pydantic import BaseModel


class CollectionsReminderRequest(BaseModel):
    invoice_id: int


class VendorEmailRequest(BaseModel):
    supplier_id: int
    context: str


class ParseOrderRequest(BaseModel):
    raw_text: str


class DraftResponse(BaseModel):
    draft_text: str
    note: str = "This is a draft only. Nothing has been sent."
