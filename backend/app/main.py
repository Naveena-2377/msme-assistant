"""
MSME Assistant backend entrypoint.

Run with:  uvicorn app.main:app --reload
(from inside backend/, with the venv active)

Then open http://127.0.0.1:8000/docs for interactive API docs (Swagger UI) —
that's the easiest way to try the /reorder/simulate endpoint by hand.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app import models  # noqa: F401  (import registers tables with Base)
from app.api import reorder, approvals, decisions, products, inventory_actions, invoices, dashboard, drafts, suppliers, customers

import os

app = FastAPI(title="MSME Assistant API", version="0.1.0")

# Local dev origins always allowed. Add your deployed frontend URL via
# the FRONTEND_URL environment variable once you have one (e.g.
# https://your-app.vercel.app) — no code change needed for that step.
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Creates all tables defined in app/models/ if they don't exist yet.
# Fine for the SQLite prototype; swap for Alembic migrations later.
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"status": "MSME Assistant backend running"}


app.include_router(reorder.router, prefix="/reorder", tags=["reorder"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(inventory_actions.router, prefix="/inventory", tags=["inventory"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
app.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])
