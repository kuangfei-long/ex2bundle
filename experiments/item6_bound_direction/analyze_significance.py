"""
Paired significance + equivalence tests for Item-6 output quality.

Establishes "no systematic quality difference across the three relaxation
strategies" as a positive statistical claim, not merely a failure to reject:

  - paired t-test and Wilcoxon signed-rank  (is there a difference?)
  - Cohen's dz effect size                   (how big?)
  - TOST equivalence test at a ±delta margin (are they statistically equivalent?)

Reads the severity record pkl written by run_bound_direction.py (which stores
per-instance ROUGE/SBERT per mode). No model re-run needed.

Usage
-----
python experiments/item6_bound_direction/analyze_significance.py \\
    --severity results/Item6/severity/item6_records.pkl --delta 0.02
"""

import argparse
import pickle
from collections import defaultdict

import numpy as np
from scipy import stats

MODES = ("symmetric", "directional", "feasopt")
METRICS = ("rouge1_f1", "rouge2_f1", "rougeL_f1", "sbert")
PAIRS = [("symmetric", "directional"), ("symmetric", "feasopt"), ("directional", "feasopt")]


def index_by_instance(records):
    by = defaultdict(dict)
    for pad in records:
        for mode in records[pad]:
            for r in records[pad][mode]:
                by[(pad, r["intent_idx"], r["target"])][mode] = r
    return by


def tost(diff, delta):
    """Two one-sided t-tests for equivalence within +/- delta; return max p."""
    se = diff.std(ddof=1) / np.sqrt(len(diff))
    m = diff.mean()
    p_lower = 1 - stats.t.cdf((m + delta) / se, len(diff) - 1)   # H0: mean <= -delta
    p_upper = stats.t.cdf((m - delta) / se, len(diff) - 1)        # H0: mean >=  delta
    return max(p_lower, p_upper)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--severity", default="results/Item6/severity/item6_records.pkl")
    ap.add_argument("--delta", type=float, default=0.02,
                    help="Equivalence margin for TOST (negligible-quality threshold).")
    args = ap.parse_args()

    with open(args.severity, "rb") as f:
        d = pickle.load(f)
    by = index_by_instance(d)
    insts = [v for v in by.values() if len(v) == 3 and v["symmetric"]["relax_freq"] > 0]
    n = len(insts)
    print(f"n = {n} paired infeasible instances | TOST margin delta = ±{args.delta}\n")

    for a, b in PAIRS:
        print(f"===== {a} vs {b} =====")
        hdr = (f"{'metric':>9} {'meanD':>8} {'95% CI':>19} {'dz':>7} "
               f"{'t p':>7} {'Wilcox p':>9} {'TOST':>7}")
        print(hdr); print("-" * len(hdr))
        for key in METRICS:
            da = np.array([v[a][key] for v in insts])
            db = np.array([v[b][key] for v in insts])
            diff = db - da
            m = diff.mean(); se = diff.std(ddof=1) / np.sqrt(n)
            dz = m / diff.std(ddof=1)
            tp = stats.ttest_rel(db, da).pvalue
            try:
                wp = stats.wilcoxon(db, da, zero_method="wilcox").pvalue
            except Exception:
                wp = float("nan")
            te = tost(diff, args.delta)
            verdict = "EQUIV" if te < 0.05 else "n.s."
            print(f"{key:>9} {m:>+8.4f} [{m-1.96*se:+.4f},{m+1.96*se:+.4f}] "
                  f"{dz:>+7.3f} {tp:>7.3f} {wp:>9.3f} {te:>6.3f} {verdict}")
        print()

    print("Reading: paired-t/Wilcoxon p>0.05 => no detectable difference; "
          "TOST p<0.05 => statistically EQUIVALENT within ±delta (positive claim).")


if __name__ == "__main__":
    main()
