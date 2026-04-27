"""
RQ1: TPC-H supplier-selection benchmark — Table 8.

Compares three methods on the task of selecting a bundle of suppliers that
satisfies intent-derived constraints (learned from 3 example bundles):
  - Random   : uniform random selection of k suppliers
  - Greedy   : top-k by summed feature score
  - Ex2Bundle: ILP with bound synthesis + ConflictRefiner relaxation

Metrics:
  - CSR (Constraint Satisfaction Rate): fraction of constraints satisfied
  - Avg objective score (sum of price/availability/balance scores)
  - Runtime (seconds)

Prerequisites
-------------
Build tpch.db from the TPC-H dbgen tool, then create the SupplierFeatures
view by running:

    CREATE TABLE SupplierFeatures AS
    SELECT
        s_suppkey   AS supplier_id,
        (1.0 - s_acctbal / 10000.0) AS price_score,
        1.0                          AS availability_score,
        CASE WHEN n.n_regionkey = 1 THEN 1.0 ELSE 0.0 END AS region_america,
        CASE WHEN n.n_regionkey = 2 THEN 1.0 ELSE 0.0 END AS region_europe,
        (s_acctbal / 10000.0)        AS balance_score
    FROM supplier s
    JOIN nation  n ON s.s_nationkey = n.n_nationkey;

Usage
-----
python experiments/run_table8_tpch.py --db_path data/tpch.db --runs 5
"""

import argparse
import logging
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sqlite3
    from docplex.mp.model import Model
    CPLEX_OK = True
except ImportError:
    CPLEX_OK = False


FEATURES = ["price_score", "availability_score", "region_america", "region_europe", "balance_score"]

# Three canonical example bundles (supplier_id lists) used in the paper.
EXAMPLE_BUNDLES = [
    [3, 12, 18, 27, 41],
    [7, 15, 23, 31, 45, 52],
    [5, 11, 19, 28, 36, 47, 58],
]


def load_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM SupplierFeatures", conn)
    conn.close()
    if df.isnull().values.any():
        logging.warning("NaN values in DB — filling with 0.5")
        df = df.fillna(0.5)
    return df


def learn_bounds(df):
    bounds = {}
    for ids in EXAMPLE_BUNDLES:
        subset = df[df["supplier_id"].isin(ids)]
        if subset.empty:
            logging.warning("Example bundle IDs %s not found in DB — skipping", ids)
            continue
        row = subset[FEATURES].sum().to_dict()
        row["count"] = len(subset)
        for k, v in row.items():
            if k not in bounds:
                bounds[k] = [v, v]
            else:
                bounds[k][0] = min(bounds[k][0], v)
                bounds[k][1] = max(bounds[k][1], v)
    return bounds


def solve_random(df, bounds):
    k = int(round((bounds["count"][0] + bounds["count"][1]) / 2))
    return df.sample(n=min(k, len(df)))


def solve_greedy(df, bounds):
    k = int(round((bounds["count"][0] + bounds["count"][1]) / 2))
    df = df.copy()
    df["_obj"] = df[["price_score", "availability_score", "balance_score"]].sum(axis=1)
    return df.sort_values("_obj", ascending=False).head(k)


def solve_ex2bundle(df, bounds):
    mdl = Model(name="Ex2Bundle_TPC_H", log_output=False)
    x = {i: mdl.binary_var(name=f"x_{i}") for i in df.index}

    mdl.maximize(mdl.sum(
        x[i] * df.loc[i, ["price_score", "availability_score", "balance_score"]].sum()
        for i in df.index
    ))

    eps = 0.01
    for f in FEATURES:
        fs = mdl.sum(x[i] * df.loc[i, f] for i in df.index)
        mdl.add_constraint(fs >= bounds[f][0] - eps, ctname=f"min_{f}")
        mdl.add_constraint(fs <= bounds[f][1] + eps, ctname=f"max_{f}")

    cnt = mdl.sum(x[i] for i in df.index)
    mdl.add_constraint(cnt >= bounds["count"][0], ctname="min_count")
    mdl.add_constraint(cnt <= bounds["count"][1], ctname="max_count")

    mdl.parameters.timelimit.set(60)
    sol = mdl.solve()
    if sol is None:
        return None
    idx = [i for i in df.index if x[i].solution_value > 0.5]
    return df.loc[idx]


def evaluate(selection, bounds):
    if selection is None or len(selection) == 0:
        return 0.0, 0.0
    agg = selection[FEATURES].sum().to_dict()
    agg["count"] = len(selection)
    keys = FEATURES + ["count"]
    sat = sum(1 for k in keys if bounds[k][0] - 0.01 <= agg[k] <= bounds[k][1] + 0.01)
    obj = agg["price_score"] + agg["availability_score"] + agg["balance_score"]
    return sat / len(keys), obj


def main():
    parser = argparse.ArgumentParser(description="Table 8 TPC-H experiment")
    parser.add_argument("--db_path", required=True, help="Path to tpch.db SQLite file")
    parser.add_argument("--runs",    type=int, default=5, help="Number of repetitions")
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    if not CPLEX_OK:
        logging.error("docplex not available — cannot run Ex2Bundle variant")

    logging.info("Loading TPC-H data from %s", args.db_path)
    df = load_data(args.db_path)
    logging.info("Loaded %d suppliers", len(df))

    bounds = learn_bounds(df)
    logging.info("Learned bounds: %s", bounds)

    results = {"Random": [], "Greedy": [], "Ex2Bundle": []}

    for run in range(1, args.runs + 1):
        logging.info("Run %d / %d", run, args.runs)

        t0 = time.time()
        csr, obj = evaluate(solve_random(df, bounds), bounds)
        results["Random"].append([csr, obj, time.time() - t0])

        t0 = time.time()
        csr, obj = evaluate(solve_greedy(df, bounds), bounds)
        results["Greedy"].append([csr, obj, time.time() - t0])

        if CPLEX_OK:
            t0 = time.time()
            sel = solve_ex2bundle(df, bounds)
            csr, obj = evaluate(sel, bounds)
            results["Ex2Bundle"].append([csr, obj, time.time() - t0])

    print("\n" + "=" * 65)
    print(f"{'Method':<12} | {'CSR':>17} | {'Avg Obj Score':>13} | {'Runtime (s)':>10}")
    print("-" * 65)
    for method, data in results.items():
        if data:
            avg_csr = np.mean([d[0] for d in data]) * 100
            avg_obj = np.mean([d[1] for d in data])
            avg_t   = np.mean([d[2] for d in data])
            print(f"{method:<12} | {avg_csr:>16.1f}% | {avg_obj:>13.2f} | {avg_t:>10.4f}")
    print("=" * 65)


if __name__ == "__main__":
    main()
