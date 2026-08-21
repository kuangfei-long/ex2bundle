"""
Item-6 (Matteo's question): do the three relaxation strategies actually produce
the SAME solution, or just the same quality score?

For each infeasible-from-start instance we run all three strategies on the same
(examples, target) and record:
  - the selected sentence ids (the bundle)
  - the final ILP objective (merit score)
  - the relaxed bounds (bound_shift = |relaxed - initial|)

We then report, across strategies:
  - how often the selected bundles are identical / their Jaccard overlap
  - relative difference in objective (merit) value
  - difference in bound shift

If bounds differ a lot but objective and solution barely differ, that supports
the hypothesis that the objective function — not the bound relaxation — drives
quality. No ROUGE/SBERT scoring here (not needed and slow).

Usage
-----
python experiments/item6_bound_direction/bench_solutions.py \\
    --data_path data/data_ctm.csv --shared_docs data/shared_docs/ \\
    --users_path data/user_summary_jsons/ \\
    --bound_pads -0.2 -0.3 -0.5 --limit 100 \\
    --out results/Item6/severity/solution_diffs.csv
"""

import argparse
import csv
import os
import random
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root

from utils.data_reader import UserDataReader
from models.ex2bundle import Ex2Bundle

MODES = ("symmetric", "directional", "feasopt")


def build_instances(udr, num_examples, num_test, limit):
    intent_doc = udr.read_intent_doc()
    sudocu = udr.read_example_summaries_sudocu()
    out = []
    for i, intent in enumerate(intent_doc):
        exsum = sudocu[i]
        if len(exsum) < num_examples + 1:
            continue
        documents = list(intent.values())[0]
        train = random.sample(range(len(exsum)), num_examples)
        test = [t for t in range(len(exsum)) if t not in train][:num_test]
        es = [exsum[t] for t in train]
        for t in test:
            out.append((i, es, documents[t]))
        if limit and len(out) >= limit:
            break
    return out[:limit] if limit else out


def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def reldiff(x, y):
    denom = max(abs(x), abs(y), 1e-9)
    return abs(x - y) / denom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_path", required=True)
    ap.add_argument("--shared_docs", required=True)
    ap.add_argument("--users_path", required=True)
    ap.add_argument("--bound_pads", nargs="+", type=float, default=[-0.2, -0.3, -0.5])
    ap.add_argument("--num_examples", type=int, default=5)
    ap.add_argument("--num_test", type=int, default=3)
    ap.add_argument("--n_topics", type=int, default=10)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7891)
    ap.add_argument("--out", default="results/Item6/severity/solution_diffs.csv")
    args = ap.parse_args()

    random.seed(args.seed)
    udr = UserDataReader(args.users_path, args.data_path, 0, 275)
    instances = build_instances(udr, args.num_examples, args.num_test, args.limit)

    rows = []
    for pad in args.bound_pads:
        models = {m: Ex2Bundle(args.data_path, args.shared_docs, args.n_topics,
                               args.num_examples, is_generative=False,
                               relaxation_mode=m, bound_pad=pad) for m in MODES}
        for k, (intent_idx, es, target) in enumerate(instances):
            rec = {}
            ok = True
            for m in MODES:
                try:
                    res = models[m].get_predicted_summary(target, es)
                except Exception:
                    ok = False; break
                if res[0].startswith("def_sum"):
                    ok = False; break
                rec[m] = dict(ids=list(models[m].last_selected_ids),
                              obj=models[m].last_objective,
                              rounds=res[4],
                              shift=models[m].last_relax_magnitude)
            if not ok:
                continue
            # only instances that actually relaxed (infeasible from start)
            if rec["symmetric"]["rounds"] <= 0:
                continue
            rows.append((pad, intent_idx, target, rec))
        print(f"pad={pad}: {sum(1 for r in rows if r[0]==pad)} infeasible instances")

    # ---- aggregate comparisons ----
    def pair_stats(mode_a, mode_b):
        jac, sol_ident, objd, shiftd = [], [], [], []
        for _, _, _, rec in rows:
            a, b = rec[mode_a], rec[mode_b]
            jac.append(jaccard(a["ids"], b["ids"]))
            sol_ident.append(1.0 if set(a["ids"]) == set(b["ids"]) else 0.0)
            if a["obj"] is not None and b["obj"] is not None:
                objd.append(reldiff(a["obj"], b["obj"]))
            shiftd.append(abs(a["shift"] - b["shift"]))
        return (np.mean(jac), np.mean(sol_ident), np.mean(objd) if objd else float("nan"),
                np.mean(shiftd))

    print(f"\nTotal infeasible instances compared: {len(rows)}\n")
    hdr = f"{'pair':>22} {'sol_identical':>13} {'mean_jaccard':>12} {'mean_obj_reldiff':>16} {'mean_boundshift_diff':>20}"
    print(hdr); print("-" * len(hdr))
    out_rows = [("pair", "sol_identical_frac", "mean_jaccard", "mean_obj_reldiff", "mean_boundshift_diff")]
    for a, b in [("symmetric", "directional"), ("symmetric", "feasopt"), ("directional", "feasopt")]:
        ji, si, od, sd = pair_stats(a, b)
        print(f"{a+' vs '+b:>22} {si:>13.3f} {ji:>12.3f} {od:>16.4f} {sd:>20.3f}")
        out_rows.append((f"{a} vs {b}", round(si, 4), round(ji, 4), round(od, 4), round(sd, 4)))

    # ---- signed objective (merit) dominance ----
    # Directional/FeasOpt relative to symmetric: is symmetric's merit higher?
    # Theory: symmetric widens both sides => feasible region is a superset of
    # directional's => symmetric merit >= directional always. FeasOpt minimizes
    # slack, not merit, so it should be lower.
    print("\nSigned objective vs symmetric  (other_obj - symmetric_obj):")
    shdr = f"{'mode':>12} {'other>sym':>10} {'equal':>7} {'other<sym':>10} {'mean_signed':>12}"
    print(shdr); print("-" * len(shdr))
    for m in ("directional", "feasopt"):
        diffs = [rec[m]["obj"] - rec["symmetric"]["obj"] for _, _, _, rec in rows
                 if rec[m]["obj"] is not None and rec["symmetric"]["obj"] is not None]
        diffs = np.array(diffs)
        hi = 100 * np.mean(diffs > 1e-6); eq = 100 * np.mean(np.abs(diffs) <= 1e-6)
        lo = 100 * np.mean(diffs < -1e-6)
        print(f"{m:>12} {hi:>9.1f}% {eq:>6.1f}% {lo:>9.1f}% {diffs.mean():>+12.4f}")
        out_rows.append((f"{m} vs symmetric (signed obj)",
                         f"higher={hi:.1f}%", f"equal={eq:.1f}%", f"lower={lo:.1f}%",
                         f"mean={diffs.mean():+.4f}"))

    # Record the sample size alongside the stats so the numbers stay traceable.
    out_rows.append(("n_infeasible_instances", len(rows), "", "", ""))
    for pad in args.bound_pads:
        out_rows.append((f"n_infeasible_pad{pad}", sum(1 for r in rows if r[0] == pad), "", "", ""))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        csv.writer(f).writerows(out_rows)
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
