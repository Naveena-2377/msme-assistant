# MSME Assistant

**A digital twin for MSME back-office operations** — it predicts what a
small trading business needs to know (demand, payment risk), simulates
the consequence of an action before it happens, and only asks a human
when a decision actually needs one.

---

## The problem this solves

MSME owners currently make reorder, collections, and payment-timing
decisions using Excel, WhatsApp, or memory. Existing tools fall into
two categories, and both fail the same way:

- **Dashboards** (Tally, Zoho Books) — show data, don't decide or act.
- **AI chatbots for business** — answer questions, don't decide or
  act, and don't check whether an action is safe before it happens.

No affordable tool for small businesses combines predictive
decision-making with a safety check before execution — and a wrong
automated action (over-ordering stock, mis-prioritizing collections)
can meaningfully hurt a small business's cash flow.

## What it actually does

**Core loop:**
```
Model predicts → Twin simulates outcome → Rule engine validates →
Approval queue (if needed) → Execute (or draft for human review)
```

Concretely: propose a stock reorder, and the system forecasts demand,
calculates the projected cash and stock impact *before* it happens,
checks that projection against safety limits (minimum cash floor,
purchase size, whether it actually fixes the problem), and either
executes it automatically (if safe) or puts it in front of you for
approval (if not). The same predict-and-prioritize pattern applies to
collections — unpaid invoices are ranked by each customer's real
payment history, not by invoice date.

**Business model this project is built for:** a small trading/
reselling MSME (e.g. a hardware or building-materials distributor) —
buys stock from suppliers, resells to business customers on 30-day
credit terms. That credit relationship is why payment-delay risk is a
real problem to solve here. See `docs/architecture.md` for the full
scope discussion, including which business types this does and
doesn't fit well.

## How to use it

1. **Dashboard** — open the app here first. At a glance: cash
   balance, products below their reorder threshold, products at
   genuine stockout risk, pending approvals, and overdue invoices.
2. **Products** — every product's stock, reorder threshold, and
   actual days-of-stock-remaining (calculated from real recent
   demand, not a fixed number). Add, edit, or delete products here,
   and assign each one to a supplier. Click a row to see that
   product's full history.
3. **Approval Queue** — propose a reorder (pick a product + quantity)
   and watch the system simulate the outcome and validate it in real
   time. Safe reorders execute immediately; risky ones wait here for
   you to approve or reject. Also includes a WhatsApp order parser —
   paste an informal order message and it extracts product names and
   quantities for you to review.
4. **Invoices** — unpaid invoices ranked by risk, using each
   customer's payment history. Draft a payment reminder (LLM-
   assisted, using Gemini) or mark an invoice as paid directly.
5. **Suppliers** — see which products each supplier provides, add or
   remove suppliers, or draft a vendor email (bulk discount requests,
   delivery follow-ups, etc.).
6. **Decision History** — every action the system has ever proposed,
   approved, rejected, or executed — filterable by type and status.
   Nothing happens silently.

## Getting started

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python data/generate_synthetic_data.py   # populates the database
uvicorn app.main:app --reload
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

**Optional — LLM-assisted drafting:**
```bash
cd backend
cp .env.example .env
# add your free Gemini API key (https://aistudio.google.com/apikey) to .env
```
Everything else in the app works without this step.

## Project structure

```
backend/
  app/
    models/   - SQLAlchemy ORM models (schema)
    ml/       - demand forecasting + payment-delay models
    twin/     - simulation layer (the "digital twin")
    rules/    - rule/safety engine
    llm/      - LLM-assisted drafting (Gemini API, draft-only)
    api/      - FastAPI route handlers
    schemas/  - Pydantic request/response schemas
  data/       - synthetic data generator + the SQLite database
frontend/
  src/
    pages/       - Dashboard, Products, Invoices, Suppliers, per-product history
    components/  - Approval Queue, Decision History
docs/
  architecture.md        - full implemented/limitations/roadmap breakdown
  evaluation_metrics.md  - real model evaluation results
  demo_script.md         - a rehearsed walkthrough for presenting this
```

## Data

All data is synthetically generated
(`backend/data/generate_synthetic_data.py`). No real business,
customer, or transaction data is used or required.

## What's implemented vs. what's roadmap

See `docs/architecture.md` for the full, honest breakdown — including
known limitations (synthetic-data-only validation, no multi-user
support yet, etc.) and what's deliberately out of scope for now
(GST automation, live banking integration, authentication/deployment).
