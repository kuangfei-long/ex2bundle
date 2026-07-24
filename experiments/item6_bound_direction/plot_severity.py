"""
Plot Item-6 metrics vs infeasibility severity (number of relaxation rounds).

Only instances that are infeasible from the start are used. Severity of an
instance = the number of relaxation rounds the iterative methods need
(symmetric's relax_freq). Instances are pooled across bound_pad values and
binned by that round count.

Panels:
  (a) mean bound shift vs rounds  (symmetric > directional > feasopt)
  (b) ROUGE-1 vs rounds           (quality parity across strategies)
  (c) SBERT vs rounds             (quality parity across strategies)

Usage
-----
python experiments/item6_bound_direction/plot_severity.py \\
    --records results/Item6/severity/item6_records.pkl \\
    --out     results/Item6/severity/fig_item6_severity.png
"""

import argparse
import pickle
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

MODES = ("symmetric", "directional", "feasopt")
COLOR = {"symmetric": "tab:red", "directional": "tab:blue", "feasopt": "tab:green"}
LABEL = {"symmetric": "Symmetric (current)", "directional": "IIS + directional", "feasopt": "FeasOpt"}
BINS = [(1, 2), (3, 4), (5, 6), (7, 9), (10, 14), (15, 99)]


def binlabel(lo, hi):
    return f"{lo}-{hi}" if hi < 90 else f"{lo}+"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="results/Item6/severity/item6_records.pkl")
    ap.add_argument("--out",     default="results/Item6/severity/fig_item6_severity.png")
    args = ap.parse_args()

    d = pickle.load(open(args.records, "rb"))
    byinst = defaultdict(dict)
    for pad in d:
        for mode in d[pad]:
            for r in d[pad][mode]:
                byinst[(pad, r["intent_idx"], r["target"])][mode] = r

    insts = [v for v in byinst.values() if len(v) == 3 and v["symmetric"]["relax_freq"] > 0]
    sev = lambda v: int(round(v["symmetric"]["relax_freq"]))

    xs, ns = [], []
    groups = []
    for lo, hi in BINS:
        grp = [v for v in insts if lo <= sev(v) <= hi]
        if grp:
            xs.append(binlabel(lo, hi)); ns.append(len(grp)); groups.append(grp)

    def series(mode, key):
        return [np.mean([v[mode][key] for v in g]) for g in groups]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    xi = range(len(xs))

    for mode in MODES:
        axes[0].plot(xi, series(mode, "bound_shift"), "o-", color=COLOR[mode], label=LABEL[mode])
        axes[1].plot(xi, series(mode, "rouge1_f1"),  "o-", color=COLOR[mode], label=LABEL[mode])
        axes[2].plot(xi, series(mode, "sbert"),      "o-", color=COLOR[mode], label=LABEL[mode])

    titles = ["(a) Bound shift vs severity",
              "(b) ROUGE-1 vs severity",
              "(c) SBERT vs severity"]
    ylabels = ["Mean bound shift", "ROUGE-1 F1", "SBERT similarity"]
    for ax, t, yl in zip(axes, titles, ylabels):
        ax.set_title(t)
        ax.set_xlabel("Relaxation rounds required (severity)")
        ax.set_ylabel(yl)
        ax.set_xticks(list(xi))
        ax.set_xticklabels([f"{x}\n(n={n})" for x, n in zip(xs, ns)], fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    plt.suptitle("Item 6: relaxation strategies vs infeasibility severity "
                 "(SubSume, infeasible-from-start instances)", y=1.03)
    plt.tight_layout()
    plt.savefig(args.out, dpi=150, bbox_inches="tight")
    print("saved", args.out)


if __name__ == "__main__":
    main()
