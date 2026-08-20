from pydantic import BaseModel


class ReorderRequest(BaseModel):
    product_id: int
    quantity: int


class DecisionResponse(BaseModel):
    decision_id: int
    action_type: str
    proposed_action: str
    simulated_outcome: str
    rule_check_result: str
    approval_status: str
    result: str | None = None

    class Config:
        from_attributes = True
