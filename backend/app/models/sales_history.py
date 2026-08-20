from sqlalchemy import Column, Integer, Date, ForeignKey
from app.database import Base


class SalesHistory(Base):
    __tablename__ = "sales_history"

    sale_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    sale_date = Column(Date, nullable=False)
    quantity_sold = Column(Integer, nullable=False)
