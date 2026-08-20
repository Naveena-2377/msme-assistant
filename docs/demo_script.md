# MSME Assistant — Demo Script

Per project spec (Dev Step 13): one full loop, rehearsed end-to-end,
is the strongest moment in any presentation. This script walks through
that loop plus enough supporting pages to show the full system without
dragging — aim for 4-5 minutes total.

Before presenting: run the data generator fresh
(`python data/generate_synthetic_data.py` from `backend/`) so the
numbers are clean and reproducible, and start both servers.

---

## 1. Open on the Dashboard (30 seconds)

"This is MSME Assistant — a digital twin for MSME back-office decisions.
At a glance: cash balance, how many products are below their reorder
threshold, how many are at genuine stockout risk, and how many
invoices are overdue. This is the first thing an owner would check
every morning."

Point out: the color coding (green = fine, amber = needs attention,
red = urgent) — no digging required to know where the problems are.

## 2. Products page — show the risk detection (30 seconds)

Click into Products. "Every product's stock, reorder threshold, and
actual days-of-stock-remaining — calculated from real recent demand,
not just a fixed number." Point at the highest-risk product (usually
Adhesive Tape Roll or similar, ~1-2 days of stock).

"Reorder threshold is a static number a business might set manually.
Days-of-stock and risk are the predictive upgrade over that — same
theme as the model-vs-baseline comparisons in the evaluation docs."

## 3. THE CORE MOMENT — propose a risky reorder (90 seconds)

This is the one to rehearse until it's smooth.

Go to Approval Queue. Propose a **deliberately oversized** reorder for
any product (e.g. 500,000 units). Click Simulate.

"Watch what happens before anything executes: the twin calculates
the projected cash balance and stock level *if* this reorder went
through — cash drops from ₹X to ₹Y, stock jumps to 500,000+. Then the
rule engine checks that projection against safety limits."

Show the result: `rejected` or `flagged`, with the reason shown.

"This didn't just log a warning — it stopped the action before any
money moved. That's the actual contribution here: not smarter
dashboards, not a chatbot that answers questions, but simulate-before-
act with an enforced safety gate."

Now propose a **reasonable** reorder for the same or a different
low-stock product. Show it auto-approve, and the stock/cash actually
update on the Products page when you flip back to it.

"Safe, routine decisions get made instantly. Only the ones that
actually need a human get surfaced — with the consequence already
worked out."

## 4. Approval Queue — human-in-the-loop (30 seconds)

If anything is sitting flagged, show approving or rejecting it live.
"Nothing flagged executes without this click."

## 5. Invoices — the other side of the business (45 seconds)

Switch to Invoices. "Same predict-and-prioritize idea, applied to
collections instead of stock — unpaid invoices ranked by each
customer's real payment history, not by invoice date."

Click "Draft Reminder" on a high-risk invoice (only if API key is
configured — otherwise skip or mention it as built-but-needs-a-key).
"LLM-assisted, draft only — never sent automatically. The owner
reviews, edits, and sends it themselves."

## 6. Decision History — the audit trail (30 seconds)

"Every action this system has ever proposed — approved, rejected, or
pending — is logged here, filterable by type and status. Nothing
happens silently; everything is queryable for 'why did X happen.'"

Click into a product from the Products page to show the per-product
filtered view as a bonus, if time allows.

## 7. Close (15 seconds)

"The individual techniques here — time-series forecasting, a
classifier, a rule engine — aren't novel on their own. What's
different is the systems-level pattern: predict, simulate the
consequence, validate against safety limits, and only then act or ask
a human. That loop is common in expensive enterprise automation and
largely absent at MSME price points — that's the gap this fills."

---

## If asked "does this work on real business data?"

Answer honestly: "Everything here is validated on synthetic data I
generated myself, disclosed explicitly in the docs. The baselines and
comparisons are real and not cherry-picked — for example, the
payment-delay model came out to an honest statistical tie against a
simple rule, which I reported as-is rather than tuning until it won.
The next real step would be validating this against an actual
business's data."

## If something breaks live

Have the Dashboard and Products page pre-loaded in a browser tab as a
fallback — those are the most visually complete and least likely to
depend on typed input going right.
