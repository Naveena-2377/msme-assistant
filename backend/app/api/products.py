"""
Products / Inventory endpoint.

Purpose: the daily-check page an MSME owner would actually look at —
every product's stock level, reorder threshold, current stockout
risk, and which supplier it's sourced from, computed the same way
the twin computes it (via estimate_daily_demand + stockout_risk_label).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Product, Supplier
from app.twin.simulate import estimate_daily_demand, stockout_risk_label

router = APIRouter()


class ProductUpdateRequest(BaseModel):
    name: str
    reorder_threshold: int
    unit_cost: float
    supplier_id: Optional[int] = None


class ProductCreateRequest(BaseModel):
    name: str
    current_stock: int = 0
    reorder_threshold: int
    unit_cost: float
    unit_price: float
    supplier_id: Optional[int] = None


@router.get("/")
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.name.asc()).all()
    suppliers_by_id = {s.supplier_id: s.name for s in db.query(Supplier).all()}
    results = []
    for p in products:
        daily_demand = estimate_daily_demand(db, p.product_id)
        days_of_stock = (p.current_stock / daily_demand) if daily_demand > 0 else None
        results.append({
            "product_id": p.product_id,
            "name": p.name,
            "current_stock": p.current_stock,
            "reorder_threshold": p.reorder_threshold,
            "below_threshold": p.current_stock < p.reorder_threshold,
            "unit_cost": p.unit_cost,
            "unit_price": p.unit_price,
            "supplier_id": p.supplier_id,
            "supplier_name": suppliers_by_id.get(p.supplier_id, "Unassigned"),
            "avg_daily_demand": round(daily_demand, 2),
            "days_of_stock": round(days_of_stock, 1) if days_of_stock is not None else None,
            "stockout_risk": stockout_risk_label(days_of_stock) if days_of_stock is not None else "unknown",
        })
    return results


@router.post("/")
def create_product(request: ProductCreateRequest, db: Session = Depends(get_db)):
    if request.supplier_id is not None:
        supplier = db.query(Supplier).filter(Supplier.supplier_id == request.supplier_id).first()
        if supplier is None:
            raise HTTPException(status_code=404, detail="Supplier not found")

    last = db.query(Product).order_by(Product.product_id.desc()).first()
    next_id = (last.product_id + 1) if last else 1

    product = Product(
        product_id=next_id,
        name=request.name,
        current_stock=request.current_stock,
        reorder_threshold=request.reorder_threshold,
        unit_cost=request.unit_cost,
        unit_price=request.unit_price,
        supplier_id=request.supplier_id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return {"product_id": product.product_id, "name": product.name}


@router.put("/{product_id}")
def update_product(product_id: int, request: ProductUpdateRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if request.supplier_id is not None:
        supplier = db.query(Supplier).filter(Supplier.supplier_id == request.supplier_id).first()
        if supplier is None:
            raise HTTPException(status_code=404, detail="Supplier not found")

    product.name = request.name
    product.reorder_threshold = request.reorder_threshold
    product.unit_cost = request.unit_cost
    product.supplier_id = request.supplier_id
    db.commit()
    db.refresh(product)

    return {
        "product_id": product.product_id,
        "name": product.name,
        "reorder_threshold": product.reorder_threshold,
        "unit_cost": product.unit_cost,
        "supplier_id": product.supplier_id,
    }


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"deleted": product_id}
