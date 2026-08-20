from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    avg_past_delay_days = Column(Float, default=0.0)
