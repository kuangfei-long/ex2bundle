"""
Plot the Item-6 bound-direction results produced by
run_bound_direction.py.

Two panels:
  (a) relaxation rate vs bound tightening (shows the stress-test knob working)
  (b) mean bound shift (relaxed-only) vs bound tightening, one line per
      relaxation strategy (the core "symmetric over-relaxes" argument)

Usage
-----
python experiments/item6_bound_direction/plot_bound_shift.py \\
    --records results/Item6/sweep/item6_records.pkl \\
    --out     results/Item6/sweep/fig_item6_bound_shift.png
"""

import argparse
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

MODES = ("symmetric", "directional", "feasopt")
COLOR = {"symmetric": "tab:red", "directional": "tab:blue", "feasopt": "tab:green"}
LABEL = {"symmetric": "Symmetric (current)", "directional": "IIS + directional", "feasopt": "FeasOpt"}


def _mean(recs, key):
    vals = [r[key] for r in recs]
    return float(np.mean(vals)) if vals else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="results/Item6/sweep/item6_records.pkl")
    ap.add_argument("--out",     default="results/Item6/sweep/fig_item6_bound_shift.png")
    args = ap.parse_args()

    with open(args.records, "rb") as f:
        data = pickle.load(f)  # {pad: {mode: [records]}}

    # x-axis: tightening = -pad (so more tightening is further right)
    pads = sorted(data.keys(), reverse=True)         # e.g. 0.1, -0.2, -0.3
    x = [-p for p in pads]

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(12, 4.5))

    # (a) relaxation rate (mode-independent; use symmetric)
    rates = []
    for p in pads:
        recs = data[p].get("symmetric", [])
        rates.append(sum(1 for r in recs if r["relax_freq"] > 0) / len(recs) if recs else np.nan)
    ax0.plot(x, [r * 100 for r in rates], "o-", color="black")
    ax0.set_xlabel("Bound tightening  (-bound_pad)")
    ax0.set_ylabel("Relaxation rate (%)")
    ax0.set_title("(a) Instances requiring relaxation")
    ax0.grid(True, alpha=0.3)

    # (b) mean bound shift on relaxed-only instances, per mode
    ns = [sum(1 for r in data[p].get("symmetric", []) if r["relax_freq"] > 0) for p in pads]
    for mode in MODES:
        ys = []
        for p in pads:
            recs = [r for r in data[p].get(mode, []) if r["relax_freq"] > 0]
            ys.append(_mean(recs, "bound_shift") if recs else np.nan)
        ax1.plot(x, ys, "o-", color=COLOR[mode], label=LABEL[mode])
    # annotate sample size at each tightening level (below the lowest curve)
    y_lo = ax1.get_ylim()[0]
    for xi, n in zip(x, ns):
        ax1.annotate(f"n={n}", (xi, y_lo), textcoords="offset points", xytext=(0, 4),
                     ha="center", va="bottom", fontsize=8, color="gray")
    ax1.set_xlabel("Bound tightening  (-bound_pad)")
    ax1.set_ylabel("Mean bound shift  (relaxed instances)")
    ax1.set_title("(b) How far bounds move to reach feasibility")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    plt.suptitle("Item 6: bound-direction relaxation on SubSume", y=1.02)
    plt.tight_layout()
    plt.savefig(args.out, dpi=150, bbox_inches="tight")
    print("saved", args.out)


if __name__ == "__main__":
    main()
