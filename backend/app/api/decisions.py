"""
Decision history endpoint (Dev Step 11).

Purpose: the "business memory" replay view — every decision ever
proposed, regardless of outcome, queryable for "why did X happen".
Unlike /approvals (which only shows pending items), this returns
everything: auto_approved, flagged, rejected, approved, and their
eventual results.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision
from app.schemas.reorder import DecisionResponse

router = APIRouter()


@router.get("/", response_model=list[DecisionResponse])
def list_decisions(
    status: Optional[str] = Query(
        None, description="Filter by approval_status: pending, approved, rejected"
    ),
    action_type: Optional[str] = Query(
        None, description="Filter by action_type: reorder, sale, stock_adjustment"
    ),
    product_id: Optional[int] = Query(
        None, description="Filter to decisions involving this product"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Decision).order_by(Decision.timestamp.desc())
    if status:
        query = query.filter(Decision.approval_status == status)
    if action_type:
        query = query.filter(Decision.action_type == action_type)

    results = query.all()

    if product_id is not None:
        # product_id lives inside the proposed_action JSON blob, not as
        # its own column, so filter in Python rather than in SQL.
        import json as _json
        filtered = []
        for d in results:
            try:
                proposed = _json.loads(d.proposed_action)
                if proposed.get("product_id") == product_id:
                    filtered.append(d)
            except (ValueError, TypeError):
                continue
        return filtered

    return results
