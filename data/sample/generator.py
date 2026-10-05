"""Synthetic retail-transactions dataset generator.

Builds a clean base dataset, then deliberately injects a documented set of
quality defects at known rates so the impact-aware ranking has something
real to demonstrate. Run directly to (re)write data/sample/retail_sample.csv.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

CATEGORIES = ["Electronics", "Apparel", "Home & Garden", "Toys", "Groceries", "Sports"]
CATEGORY_VARIANTS = {
    "Electronics": ["Electronics", "electronics", " Electronics ", "ELECTRONICS"],
    "Apparel": ["Apparel", "apparel", "Appparel"],
}


def generate_retail_dataset(n_rows: int = 5000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pyrand = random.Random(seed)

    # Anchor dates to "now" so the freshness pillar has a realistic mix of
    # recent and genuinely stale (>180 day) records, regardless of when this
    # generator is run.
    now = datetime.now()
    base_date = now - timedelta(days=270)
    order_dates = [base_date + timedelta(days=int(d)) for d in rng.integers(0, 270, size=n_rows)]
    last_updated = [d + timedelta(hours=int(h)) for d, h in zip(order_dates, rng.integers(0, 48, size=n_rows))]

    df = pd.DataFrame({
        "order_id": [f"ORD-{100000 + i}" for i in range(n_rows)],
        "customer_id": [f"CUST-{rng.integers(1, 1200)}" for _ in range(n_rows)],
        "order_date": order_dates,
        "last_updated": last_updated,
        "category": rng.choice(CATEGORIES, size=n_rows),
        "quantity": rng.integers(1, 10, size=n_rows),
        "unit_price": np.round(rng.uniform(3, 500, size=n_rows), 2),
        "discount_pct": np.round(rng.uniform(0, 0.3, size=n_rows), 3),
        "customer_email": [f"user{rng.integers(1, 1200)}@example.com" for _ in range(n_rows)],
        "customer_phone": [f"555-{rng.integers(100,999)}-{rng.integers(1000,9999)}" for _ in range(n_rows)],
        "region": rng.choice(["North", "South", "East", "West"], size=n_rows),
    })

    n = len(df)

    # --- Inject documented defects (rates are intentional and recorded below) ---
    defect_log = {}

    # 1. Missing values (~4% of customer_email, ~2% of region)
    email_missing_idx = rng.choice(n, size=int(0.04 * n), replace=False)
    df.loc[email_missing_idx, "customer_email"] = np.nan
    region_missing_idx = rng.choice(n, size=int(0.02 * n), replace=False)
    df.loc[region_missing_idx, "region"] = np.nan
    defect_log["missing_email_pct"] = round(100 * len(email_missing_idx) / n, 2)
    defect_log["missing_region_pct"] = round(100 * len(region_missing_idx) / n, 2)

    # 2. Duplicate rows (~1.5%)
    dup_sample = df.sample(int(0.015 * n), random_state=seed)
    df = pd.concat([df, dup_sample], ignore_index=True)
    n = len(df)
    defect_log["duplicate_rows_injected"] = len(dup_sample)

    # 3. Invalid quantity (negative) -- ~1.96% of records, matching the historical reference scenario
    neg_qty_idx = rng.choice(n, size=int(0.0196 * n), replace=False)
    df.loc[neg_qty_idx, "quantity"] = -df.loc[neg_qty_idx, "quantity"]
    defect_log["invalid_quantity_pct"] = round(100 * len(neg_qty_idx) / n, 2)

    # 4. Non-positive price -- ~0.46% of records
    zero_price_idx = rng.choice(n, size=max(1, int(0.0046 * n)), replace=False)
    df.loc[zero_price_idx, "unit_price"] = 0.0
    defect_log["nonpositive_price_pct"] = round(100 * len(zero_price_idx) / n, 2)

    # 5. Inconsistent category labels (~3%)
    inconsistent_idx = rng.choice(n, size=int(0.03 * n), replace=False)
    for idx in inconsistent_idx:
        cat = df.at[idx, "category"]
        variants = CATEGORY_VARIANTS.get(cat, [cat.lower(), cat.upper(), f" {cat} "])
        df.at[idx, "category"] = pyrand.choice(variants)
    defect_log["inconsistent_category_pct"] = round(100 * len(inconsistent_idx) / n, 2)

    # 6. Outliers in unit_price (~0.5%)
    outlier_idx = rng.choice(n, size=max(1, int(0.005 * n)), replace=False)
    df.loc[outlier_idx, "unit_price"] = df.loc[outlier_idx, "unit_price"] * 50
    defect_log["price_outlier_pct"] = round(100 * len(outlier_idx) / n, 2)

    # 7. Date errors: a few unparseable strings, a few future dates
    bad_date_idx = rng.choice(n, size=max(1, int(0.004 * n)), replace=False)
    df["order_date"] = df["order_date"].astype(object)
    df.loc[bad_date_idx, "order_date"] = "31/02/2025"  # invalid calendar date
    future_idx = rng.choice(n, size=max(1, int(0.003 * n)), replace=False)
    df.loc[future_idx, "order_date"] = datetime(2030, 1, 1)
    defect_log["invalid_date_pct"] = round(100 * len(bad_date_idx) / n, 2)
    defect_log["future_date_pct"] = round(100 * len(future_idx) / n, 2)

    # 8. Schema/conformity violation: a few quantity values stored as text
    text_qty_idx = rng.choice(n, size=max(1, int(0.006 * n)), replace=False)
    df["quantity"] = df["quantity"].astype(object)
    df.loc[text_qty_idx, "quantity"] = "N/A"

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df, defect_log


if __name__ == "__main__":
    df, defects = generate_retail_dataset()
    out_path = os.path.join(os.path.dirname(__file__), "retail_sample.csv")
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print("Injected defect rates (documented, reproducible with seed=7):")
    for k, v in defects.items():
        print(f"  {k}: {v}%")
