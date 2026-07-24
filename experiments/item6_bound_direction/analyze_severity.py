"""
Analyze infeasibility severity from the Item-6 record pkls (no model re-run).

Answers two reviewer questions:
  (1) How common is (severe) infeasibility?  -> base rate + round distribution.
  (2) Do the quality/bound trends hold as severity grows?  -> per-instance
      metrics binned by the number of relaxation rounds the iterative methods
      need (symmetric's relax_freq).

Reads the record pkls written by run_bound_direction.py:
  - baseline pkl (default bound_pad=0.1)          -> natural infeasibility rate
  - sweep pkl (mild/moderate tightening)          -> round distribution
  - severity pkl (aggressive tightening)          -> severity-binned metrics

Usage
-----
python experiments/item6_bound_direction/analyze_severity.py \\
    --baseline results/Item6/baseline/item6_records.pkl \\
    --sweep    results/Item6/sweep/item6_records.pkl \\
    --severity results/Item6/severity/item6_records.pkl
"""

import argparse
import pickle
from collections import Counter, defaultdict

import numpy as np

MODES = ("symmetric", "directional", "feasopt")
BINS = [(1, 2), (3, 4), (5, 6), (7, 9), (10, 14), (15, 99)]


def load(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def index_by_instance(records):
    """records: {pad: {mode: [rec]}} -> {(pad,intent,target): {mode: rec}}."""
    by = defaultdict(dict)
    for pad in records:
        for mode in records[pad]:
            for r in records[pad][mode]:
                by[(pad, r["intent_idx"], r["target"])][mode] = r
    return by


def base_rate(baseline_path):
    """Natural infeasibility rate at the default bound synthesis (pad=0.1)."""
    b = load(baseline_path)
    # baseline pkl is the old flat format {mode: [rec]} (single default pad).
    sym = b["symmetric"] if "symmetric" in b else list(index_by_instance(b).values())
    if isinstance(sym, list) and sym and isinstance(sym[0], dict) and "relax_freq" in sym[0]:
        recs = sym
    else:  # sweep-format fallback: take pad 0.1 if present
        recs = b.get(0.1, {}).get("symmetric", [])
    inf = sum(1 for r in recs if r["relax_freq"] > 0)
    print(f"[base rate] default bounds: {inf}/{len(recs)} = {100*inf/len(recs):.1f}% infeasible")


def round_distribution(sweep_path, pads=(-0.2, -0.3)):
    d = load(sweep_path)
    for pad in pads:
        if pad not in d:
            continue
        rounds = [int(round(r["relax_freq"])) for r in d[pad]["symmetric"] if r["relax_freq"] > 0]
        if not rounds:
            continue
        tot = len(rounds); c = Counter(rounds); cum = 0
        print(f"\n[rounds @ pad={pad}] {tot}/{len(d[pad]['symmetric'])} infeasible "
              f"({100*tot/len(d[pad]['symmetric']):.0f}%), median={np.median(rounds):.0f}")
        for r in sorted(c):
            cum += c[r]
            print(f"    {r:>2} round(s): {c[r]:>3}  ({100*cum/tot:>3.0f}% cumulative)")
        print(f"    <=2 rounds: {100*sum(1 for x in rounds if x<=2)/tot:.0f}%")


def severity_binned(severity_path):
    d = load(severity_path)
    by = index_by_instance(d)
    insts = [v for v in by.values() if len(v) == 3 and v["symmetric"]["relax_freq"] > 0]
    sev = lambda v: int(round(v["symmetric"]["relax_freq"]))
    print(f"\n[severity-binned] {len(insts)} infeasible instances "
          f"(pooled across pads, binned by rounds)")
    hdr = (f"{'rounds':>7} {'n':>4} | {'ROUGE-1 s/d/f':>22} | "
           f"{'SBERT s/d/f':>22} | {'bound_shift s/d/f':>24}")
    print(hdr); print("-" * len(hdr))
    for lo, hi in BINS:
        grp = [v for v in insts if lo <= sev(v) <= hi]
        if not grp:
            continue
        mm = lambda mode, key: np.mean([v[mode][key] for v in grp])
        r1 = [mm(m, "rouge1_f1") for m in MODES]
        sb = [mm(m, "sbert") for m in MODES]
        bs = [mm(m, "bound_shift") for m in MODES]
        lbl = f"{lo}-{hi}" if hi < 90 else f"{lo}+"
        print(f"{lbl:>7} {len(grp):>4} | {r1[0]:.3f}/{r1[1]:.3f}/{r1[2]:.3f}      | "
              f"{sb[0]:.3f}/{sb[1]:.3f}/{sb[2]:.3f}      | {bs[0]:.2f}/{bs[1]:.2f}/{bs[2]:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="results/Item6/baseline/item6_records.pkl")
    ap.add_argument("--sweep",    default="results/Item6/sweep/item6_records.pkl")
    ap.add_argument("--severity", default="results/Item6/severity/item6_records.pkl")
    args = ap.parse_args()

    base_rate(args.baseline)
    round_distribution(args.sweep)
    severity_binned(args.severity)


if __name__ == "__main__":
    main()
