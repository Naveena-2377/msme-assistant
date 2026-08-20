"""
Import every model here so that Base.metadata.create_all() (called from
main.py) picks up all tables in one shot.
"""

from app.models.product import Product
from app.models.sales_history import SalesHistory
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.supplier import Supplier
from app.models.cash_ledger import CashLedger
from app.models.decision import Decision

__all__ = [
    "Product",
    "SalesHistory",
    "Customer",
    "Invoice",
    "Supplier",
    "CashLedger",
    "Decision",
]
