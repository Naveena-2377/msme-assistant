from sqlalchemy import Column, Integer, String, Float, Date
from app.database import Base


class CashLedger(Base):
    __tablename__ = "cash_ledger"

    entry_id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    transaction_type = Column(String)  # sale | purchase | payment_received | payment_made
    amount = Column(Float, nullable=False)
    running_balance = Column(Float, nullable=False)
