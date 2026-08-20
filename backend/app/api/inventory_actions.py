"""
Sales recording and manual stock adjustment endpoints.

Both are logged into the same `decisions` table as reorders, so the
Decision History page shows one unified audit trail — every way stock
or cash ever changed, not just reorder activity.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision
from app.schemas.inventory_actions import SaleRequest, StockAdjustmentRequest
from app.schemas.reorder import DecisionResponse
from app.twin.simulate import record_sale, adjust_stock

router = APIRouter()


def _next_decision_id(db) -> int:
    last = db.query(Decision).order_by(Decision.decision_id.desc()).first()
    return (last.decision_id + 1) if last else 1


@router.post("/sales", response_model=DecisionResponse)
def create_sale(request: SaleRequest, db: Session = Depends(get_db)):
    try:
        result = record_sale(db, request.product_id, request.quantity, request.unit_price)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    decision = Decision(
        decision_id=_next_decision_id(db),
        action_type="sale",
        proposed_action=json.dumps({
            "product_id": request.product_id,
            "quantity": request.quantity,
            "unit_price": request.unit_price,
        }),
        simulated_outcome=json.dumps(result),  # no "simulation" step for a real sale — result is the fact
        rule_check_result="not_applicable",
        approval_status="approved",
        result=json.dumps(result),
        timestamp=datetime.utcnow(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.post("/stock-adjustments", response_model=DecisionResponse)
def create_stock_adjustment(request: StockAdjustmentRequest, db: Session = Depends(get_db)):
    try:
        result = adjust_stock(db, request.product_id, request.new_stock)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    decision = Decision(
        decision_id=_next_decision_id(db),
        action_type="stock_adjustment",
        proposed_action=json.dumps({
            "product_id": request.product_id,
            "new_stock": request.new_stock,
            "reason": request.reason,
        }),
        simulated_outcome=json.dumps({**result, "reason": request.reason}),
        rule_check_result="not_applicable",
        approval_status="approved",
        result=json.dumps(result),
        timestamp=datetime.utcnow(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision
