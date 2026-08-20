"""
Approval queue endpoints — the human-in-the-loop layer. Every action
the rule engine flagged (not auto-approved, not rejected) sits here
until a person approves or rejects it. Nothing flagged executes
without this step.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision
from app.schemas.reorder import DecisionResponse
from app.twin.simulate import execute_reorder

router = APIRouter()


@router.get("/", response_model=list[DecisionResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    return db.query(Decision).filter(Decision.approval_status == "pending").all()


@router.post("/{decision_id}/approve", response_model=DecisionResponse)
def approve_decision(decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(Decision).filter(Decision.decision_id == decision_id).first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.approval_status != "pending":
        raise HTTPException(status_code=400, detail=f"Decision already {decision.approval_status}")

    if decision.action_type == "reorder":
        proposed = json.loads(decision.proposed_action)
        exec_outcome = execute_reorder(db, proposed["product_id"], proposed["quantity"])
        decision.result = json.dumps(exec_outcome)

    decision.approval_status = "approved"
    db.commit()
    db.refresh(decision)
    return decision


@router.post("/{decision_id}/reject", response_model=DecisionResponse)
def reject_decision(decision_id: int, db: Session = Depends(get_db)):
    decision = db.query(Decision).filter(Decision.decision_id == decision_id).first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.approval_status != "pending":
        raise HTTPException(status_code=400, detail=f"Decision already {decision.approval_status}")

    decision.approval_status = "rejected"
    decision.result = json.dumps({"note": "Rejected by human reviewer."})
    db.commit()
    db.refresh(decision)
    return decision
