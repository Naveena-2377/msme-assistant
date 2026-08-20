"""
Demand forecasting model (Dev Step 3).

Purpose: predict per-product demand over the next N days to drive
reorder quantity, and prove it beats a static-threshold baseline
(what a non-ML business would use today).

Run directly to see the comparison table:
    python -m app.ml.demand_forecasting
(run from backend/, so `app` resolves as a package)

Model choice: statsmodels Holt-Winters (Exponential Smoothing) —
one of the time-series options explicitly allowed in the project spec
(Prophet / ARIMA / small LSTM). Chosen over Prophet here because it
needs no C++/Stan compiler toolchain, so it installs cleanly on any
machine including plain Windows.

Baseline:  next-day demand = average of the last 7 days' sales
           (this is literally what most MSME owners do by hand)

Evaluation: MAE and RMSE on a held-out 30-day test window, per
product and averaged across all products.
"""

import warnings
from datetime import timedelta

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.database import SessionLocal
from app.models import Product, SalesHistory

warnings.filterwarnings("ignore")

TEST_DAYS = 30       # holdout window for evaluation
BASELINE_WINDOW = 7  # "average of last N days" baseline
SEASONAL_PERIOD = 7  # weekly seasonality


def load_sales_dataframe(db, product_id: int) -> pd.DataFrame:
    """Returns a dataframe with columns: ds (date), y (quantity), continuous daily."""
    rows = (
        db.query(SalesHistory)
        .filter(SalesHistory.product_id == product_id)
        .order_by(SalesHistory.sale_date)
        .all()
    )
    df = pd.DataFrame([{"ds": r.sale_date, "y": r.quantity_sold} for r in rows])
    if df.empty:
        return df

    # Fill missing dates with 0 sales — needed for a continuous daily series.
    full_range = pd.date_range(df["ds"].min(), df["ds"].max(), freq="D")
    df = (
        df.set_index("ds")
        .reindex(full_range, fill_value=0)
        .rename_axis("ds")
        .reset_index()
    )
    return df


def train_test_split(df: pd.DataFrame, test_days: int = TEST_DAYS):
    split_point = df["ds"].max() - timedelta(days=test_days)
    train = df[df["ds"] <= split_point].copy()
    test = df[df["ds"] > split_point].copy()
    return train, test


def baseline_forecast(train: pd.DataFrame, horizon: int) -> np.ndarray:
    """Static-threshold baseline: repeat the average of the last N days."""
    avg = train["y"].tail(BASELINE_WINDOW).mean()
    return np.full(horizon, avg)


def holtwinters_forecast(train: pd.DataFrame, horizon: int) -> np.ndarray:
    series = train.set_index("ds")["y"]
    # Add a tiny constant so multiplicative seasonality tolerates zero days.
    model = ExponentialSmoothing(
        series + 0.01,
        trend="add",
        seasonal="add",
        seasonal_periods=SEASONAL_PERIOD,
        initialization_method="estimated",
    ).fit()
    forecast = model.forecast(horizon)
    return np.clip(forecast.values - 0.01, a_min=0, a_max=None)


def mae(y_true, y_pred):
    return float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))


def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.array(y_true) - np.array(y_pred)) ** 2)))


def evaluate_product(db, product: Product) -> dict:
    df = load_sales_dataframe(db, product.product_id)
    if len(df) < TEST_DAYS + 60:  # need at least a couple seasonal cycles
        return None

    train, test = train_test_split(df)
    horizon = len(test)

    baseline_pred = baseline_forecast(train, horizon)
    model_pred = holtwinters_forecast(train, horizon)
    actual = test["y"].values

    return {
        "product": product.name,
        "baseline_mae": round(mae(actual, baseline_pred), 2),
        "model_mae": round(mae(actual, model_pred), 2),
        "baseline_rmse": round(rmse(actual, baseline_pred), 2),
        "model_rmse": round(rmse(actual, model_pred), 2),
    }


def main():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        results = []
        for product in products:
            print(f"Evaluating: {product.name} ...")
            try:
                result = evaluate_product(db, product)
            except Exception as e:
                print(f"  skipped ({e})")
                result = None
            if result:
                results.append(result)

        if not results:
            print("Not enough sales history to evaluate. Run the data generator first.")
            return

        df_results = pd.DataFrame(results)
        print("\n=== Per-product results ===")
        print(df_results.to_string(index=False))

        avg_baseline_mae = df_results["baseline_mae"].mean()
        avg_model_mae = df_results["model_mae"].mean()
        avg_baseline_rmse = df_results["baseline_rmse"].mean()
        avg_model_rmse = df_results["model_rmse"].mean()
        mae_improvement = (avg_baseline_mae - avg_model_mae) / avg_baseline_mae * 100
        rmse_improvement = (avg_baseline_rmse - avg_model_rmse) / avg_baseline_rmse * 100

        print("\n=== Overall (averaged across products) ===")
        print(f"Baseline      MAE: {avg_baseline_mae:.2f}   RMSE: {avg_baseline_rmse:.2f}")
        print(f"Holt-Winters  MAE: {avg_model_mae:.2f}   RMSE: {avg_model_rmse:.2f}")
        print(f"MAE improvement over baseline:  {mae_improvement:.1f}%")
        print(f"RMSE improvement over baseline: {rmse_improvement:.1f}%")
    finally:
        db.close()


if __name__ == "__main__":
    main()
