"""
Suppliers endpoint. Lists suppliers (with which products they supply,
now that products link to a supplier) and lets the owner add or
remove suppliers.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Supplier, Product

router = APIRouter()


class SupplierCreateRequest(BaseModel):
    name: str
    avg_delivery_days: float
    reliability_score: float


@router.get("/")
def list_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).order_by(Supplier.name.asc()).all()
    products = db.query(Product).all()
    results = []
    for s in suppliers:
        supplied = [p.name for p in products if p.supplier_id == s.supplier_id]
        results.append({
            "supplier_id": s.supplier_id,
            "name": s.name,
            "avg_delivery_days": s.avg_delivery_days,
            "reliability_score": s.reliability_score,
            "products_supplied": supplied,
        })
    return results


@router.post("/")
def create_supplier(request: SupplierCreateRequest, db: Session = Depends(get_db)):
    last = db.query(Supplier).order_by(Supplier.supplier_id.desc()).first()
    next_id = (last.supplier_id + 1) if last else 1

    supplier = Supplier(
        supplier_id=next_id,
        name=request.name,
        avg_delivery_days=request.avg_delivery_days,
        reliability_score=request.reliability_score,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return {"supplier_id": supplier.supplier_id, "name": supplier.name}


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    linked_products = db.query(Product).filter(Product.supplier_id == supplier_id).count()
    if linked_products > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {linked_products} product(s) are still assigned to this supplier. Reassign them first.",
        )

    db.delete(supplier)
    db.commit()
    return {"deleted": supplier_id}
