"""
Payment-delay prediction model (Dev Step 4).

Purpose: predict whether a given invoice will be paid late, so
collections effort can be prioritized toward customers actually at
risk of delay instead of chased in issue-date order.

Run directly to see the comparison table:
    python -m app.ml.payment_delay
(run from backend/, so `app` resolves as a package)

IMPORTANT — avoiding data leakage:
Each invoice's "customer historical avg delay" feature is computed
only from that customer's invoices issued *before* the current one
(an expanding window), never from future invoices. The train/test
split is also done by issue_date (not randomly shuffled), since
shuffling a time-ordered business process leaks future information
into training. This is what makes the evaluation numbers trustworthy.

Target: 1 if the invoice was paid after its due_date, 0 if on time.
Only invoices that have actually been paid are used (status='paid'),
since unpaid/pending invoices don't have a ground-truth label yet.

Baseline: static rule — "flag as late if this customer's historical
average delay > 3 days" (what a human doing this by memory would
roughly do).

Evaluation: precision, recall, F1 on a held-out time-based test split.
"""

import warnings

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score

from app.database import SessionLocal
from app.models import Invoice

warnings.filterwarnings("ignore")

STATIC_RULE_THRESHOLD_DAYS = 3  # baseline: flag late if customer's past avg delay exceeds this
TEST_FRACTION = 0.2             # last 20% of invoices by issue_date held out for testing


def load_invoice_dataframe(db) -> pd.DataFrame:
    rows = db.query(Invoice).filter(Invoice.paid_date.isnot(None)).all()
    df = pd.DataFrame([{
        "invoice_id": r.invoice_id,
        "customer_id": r.customer_id,
        "amount": r.amount,
        "issue_date": r.issue_date,
        "due_date": r.due_date,
        "paid_date": r.paid_date,
    } for r in rows])
    df = df.sort_values("issue_date").reset_index(drop=True)
    df["delay_days"] = (df["paid_date"] - df["due_date"]).apply(lambda x: x.days)
    df["is_late"] = (df["delay_days"] > 0).astype(int)
    return df


def add_expanding_customer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each invoice, compute the issuing customer's average delay and
    invoice count using only invoices from that customer with an
    earlier issue_date — an expanding window, so no future leakage.
    """
    df = df.copy()
    df["customer_avg_delay_so_far"] = 0.0
    df["customer_invoice_count_so_far"] = 0

    history = {}  # customer_id -> list of delay_days seen so far
    for idx, row in df.iterrows():
        cust = row["customer_id"]
        past = history.get(cust, [])
        df.at[idx, "customer_avg_delay_so_far"] = np.mean(past) if past else 0.0
        df.at[idx, "customer_invoice_count_so_far"] = len(past)
        history.setdefault(cust, []).append(row["delay_days"])

    df["issue_month"] = pd.to_datetime(df["issue_date"]).dt.month
    df["issue_weekday"] = pd.to_datetime(df["issue_date"]).dt.weekday
    return df


def time_based_split(df: pd.DataFrame, test_fraction: float = TEST_FRACTION):
    split_idx = int(len(df) * (1 - test_fraction))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def baseline_predict(df: pd.DataFrame) -> np.ndarray:
    return (df["customer_avg_delay_so_far"] > STATIC_RULE_THRESHOLD_DAYS).astype(int).values


FEATURE_COLS = [
    "amount", "customer_avg_delay_so_far",
    "customer_invoice_count_so_far", "issue_month", "issue_weekday",
]


def train_model(train: pd.DataFrame) -> XGBClassifier:
    model = XGBClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
    )
    model.fit(train[FEATURE_COLS], train["is_late"])
    return model


def evaluate(y_true, y_pred, label: str) -> dict:
    return {
        "approach": label,
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 3),
    }


def main():
    db = SessionLocal()
    try:
        print("Loading paid invoices...")
        df = load_invoice_dataframe(db)
        print(f"Loaded {len(df)} paid invoices.")

        print("Building expanding-window customer features (leakage-safe)...")
        df = add_expanding_customer_features(df)

        train, test = time_based_split(df)
        print(f"Train: {len(train)} invoices (earlier) | Test: {len(test)} invoices (later)")
        print(f"Test set late-payment rate: {test['is_late'].mean():.1%}")

        baseline_pred = baseline_predict(test)
        baseline_result = evaluate(test["is_late"], baseline_pred, "Static rule (baseline)")

        model = train_model(train)
        model_pred = model.predict(test[FEATURE_COLS])
        model_result = evaluate(test["is_late"], model_pred, "XGBoost")

        results_df = pd.DataFrame([baseline_result, model_result])
        print("\n=== Results (held-out, time-based test split) ===")
        print(results_df.to_string(index=False))

        f1_improvement = (
            (model_result["f1"] - baseline_result["f1"])
            / max(baseline_result["f1"], 1e-9) * 100
        )
        print(f"\nF1 improvement over baseline: {f1_improvement:.1f}%")

        print("\n=== Feature importance (XGBoost) ===")
        importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
        print(importances.sort_values(ascending=False).round(3).to_string())
    finally:
        db.close()


if __name__ == "__main__":
    main()
