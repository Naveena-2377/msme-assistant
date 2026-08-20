from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    avg_delivery_days = Column(Float)
    reliability_score = Column(Float)  # 0-1
