from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class Decision(Base):
    """
    The 'business memory' log. Every proposed action, its simulated
    outcome, whether it passed rule checks, human approval status, and
    the eventual result — timestamped and queryable for replay.
    """

    __tablename__ = "decisions"

    decision_id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String)  # reorder | collections_priority | vendor_payment
    proposed_action = Column(Text)
    simulated_outcome = Column(Text)  # JSON string: projected cash, stock, risk
    rule_check_result = Column(String)  # auto_approved | flagged | rejected
    approval_status = Column(String, default="pending")  # pending | approved | rejected
    result = Column(Text, nullable=True)  # filled in after execution
    timestamp = Column(DateTime)
