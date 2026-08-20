from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    current_stock = Column(Integer, default=0)
    reorder_threshold = Column(Integer, default=0)
    unit_cost = Column(Float)
    unit_price = Column(Float)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=True)
