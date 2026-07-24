"""
Clean runtime benchmark for the three Item-6 relaxation strategies.

Motivation: the runtime numbers from run_bound_direction.py are not
comparable across strategies, because that sweep was killed and resumed across
multiple processes under variable laptop load. This script isolates a fair
runtime comparison:

  * single process, one shot (no checkpoint/resume);
  * the three strategies run back-to-back on the SAME instance, so any load
    drift is shared across all three;
  * NO ROUGE/SBERT scoring (irrelevant to solver runtime and the main slowdown);
  * each instance timed `--repeats` times, median taken to damp noise.

Only model time (get_predicted_summary) is measured. Results are binned by the
number of relaxation rounds the iterative methods need (severity).

Usage
-----
python experiments/item6_bound_direction/bench_runtime.py \\
    --data_path data/data_ctm.csv --shared_docs data/shared_docs/ \\
    --users_path data/user_summary_jsons/ \\
    --bound_pad -0.5 --limit 80 --repeats 3 \\
    --out results/Item6/severity/runtime_bench.csv
"""

import argparse
import csv
import os
import random
import sys
import time
import warnings
from collections import defaultdict

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root

from utils.data_reader import UserDataReader
from models.ex2bundle import Ex2Bundle

MODES = ("symmetric", "directional", "feasopt")
BINS = [(1, 2), (3, 4), (5, 6), (7, 9), (10, 14), (15, 99)]


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
            out.append((es, documents[t]))
        if limit and len(out) >= limit:
            break
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_path", required=True)
    ap.add_argument("--shared_docs", required=True)
    ap.add_argument("--users_path", required=True)
    ap.add_argument("--bound_pad", type=float, default=-0.5)
    ap.add_argument("--num_examples", type=int, default=5)
    ap.add_argument("--num_test", type=int, default=3)
    ap.add_argument("--n_topics", type=int, default=10)
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7891)
    ap.add_argument("--out", default="results/Item6/severity/runtime_bench.csv")
    args = ap.parse_args()

    random.seed(args.seed)
    udr = UserDataReader(args.users_path, args.data_path, 0, 275)
    instances = build_instances(udr, args.num_examples, args.num_test, args.limit)
    print(f"{len(instances)} instances, bound_pad={args.bound_pad}, repeats={args.repeats}")

    # one model per mode, created once (avoids reloading embeddings)
    models = {m: Ex2Bundle(args.data_path, args.shared_docs, args.n_topics,
                           args.num_examples, is_generative=False,
                           relaxation_mode=m, bound_pad=args.bound_pad)
              for m in MODES}

    rows = []  # (rounds, t_sym, t_dir, t_feas)
    for k, (es, target) in enumerate(instances):
        if k % 10 == 0:
            print(f"  {k}/{len(instances)}")
        times = defaultdict(list)
        rounds = None
        ok = True
        for _ in range(args.repeats):
            for m in MODES:                      # back-to-back on the same instance
                t0 = time.perf_counter()
                try:
                    res = models[m].get_predicted_summary(target, es)
                except Exception:
                    ok = False
                    break
                dt = time.perf_counter() - t0
                if res[0].startswith("def_sum"):
                    ok = False
                    break
                times[m].append(dt)
                if m == "symmetric":
                    rounds = res[4]
            if not ok:
                break
        if not ok or rounds is None or rounds <= 0:
            continue                             # skip feasible / errored
        rows.append((int(round(rounds)),
                     float(np.median(times["symmetric"])),
                     float(np.median(times["directional"])),
                     float(np.median(times["feasopt"]))))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rounds", "sym_s", "dir_s", "feas_s"])
        w.writerows(rows)

    # binned summary
    print(f"\n{len(rows)} infeasible instances timed\n")
    hdr = f"{'rounds':>7} {'n':>4} {'sym_s':>8} {'dir_s':>8} {'feas_s':>8}   {'feas/sym':>9}"
    print(hdr); print("-" * len(hdr))
    for lo, hi in BINS:
        grp = [r for r in rows if lo <= r[0] <= hi]
        if not grp:
            continue
        s = np.median([r[1] for r in grp]); dd = np.median([r[2] for r in grp]); fe = np.median([r[3] for r in grp])
        lbl = f"{lo}-{hi}" if hi < 90 else f"{lo}+"
        print(f"{lbl:>7} {len(grp):>4} {s:>8.3f} {dd:>8.3f} {fe:>8.3f}   {fe/s:>8.2f}x")


if __name__ == "__main__":
    main()
