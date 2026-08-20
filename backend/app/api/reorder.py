"""
Reorder endpoint — this is where the full MSME Assistant loop actually runs:

    proposed action -> twin simulates outcome -> rule engine validates
    -> auto-execute (if safe) OR sit in the approval queue (if not)

This is the strongest demo endpoint in the whole project: one POST
call proves the entire "predict -> simulate -> validate -> approve"
pattern from the spec.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision
from app.schemas.reorder import ReorderRequest, DecisionResponse
from app.twin.simulate import simulate_reorder, execute_reorder
from app.rules.rule_engine import check_reorder

router = APIRouter()


@router.post("/simulate", response_model=DecisionResponse)
def propose_reorder(request: ReorderRequest, db: Session = Depends(get_db)):
    """
    Propose a reorder. Runs it through the full loop:
    simulate -> rule check -> auto-execute if safe, else queue for approval.
    Always logs the decision (the "business memory"), regardless of outcome.
    """
    try:
        outcome = simulate_reorder(db, request.product_id, request.quantity)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    rule_result = check_reorder(outcome)

    last_decision = db.query(Decision).order_by(Decision.decision_id.desc()).first()
    next_id = (last_decision.decision_id + 1) if last_decision else 1

    execution_result = None
    approval_status = "pending"

    if rule_result["result"] == "auto_approved":
        exec_outcome = execute_reorder(db, request.product_id, request.quantity)
        execution_result = json.dumps(exec_outcome)
        approval_status = "approved"
    elif rule_result["result"] == "rejected":
        approval_status = "rejected"
        execution_result = json.dumps({"note": "Rejected by rule engine — not executed."})
    # if "flagged", it stays "pending" and sits in the approval queue for a human.

    decision = Decision(
        decision_id=next_id,
        action_type="reorder",
        proposed_action=json.dumps({"product_id": request.product_id, "quantity": request.quantity}),
        simulated_outcome=json.dumps(outcome),
        rule_check_result=rule_result["result"],
        approval_status=approval_status,
        result=execution_result,
        timestamp=datetime.utcnow(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    return decision
