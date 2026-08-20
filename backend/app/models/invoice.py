from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    amount = Column(Float, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)  # NULL if unpaid
    status = Column(String, default="pending")  # paid | overdue | pending
