"""
SketchRefine scalability comparison (Paper Section 4.5).

Compares the DIRECT retrieval method (Section 4.3: one CPLEX ILP over the
whole SBERT-prefiltered candidate pool) against SKETCH-REFINE (Section 4.5:
`utils/sketch_refine.py`'s SketchRefineSolver, `models/ex2bundle.py`'s
`do_sketch_refine=True`) on the SubSumE dataset under the RQ2 setting (5
source / 3 target summaries per intent, same as `experiments/run_figure9_subsume.py`
and `experiments/item6_bound_direction`).

For every (method, instance) we record: runtime (wall/learn/ILP), summary
quality (ROUGE-1/2/L, SBERT), summary length, and relaxation counts, binned by
the target package length (`avg_len`, which sets the candidate-pool size --
see `models/ex2bundle.py:get_predicted_summary`, `pool_size = avg_len * 10`)
so the runtime curves show how each method scales as the problem grows.

Both methods are evaluated on the *identical* instances (same model, same
bounds, same candidate pool) so the comparison is apples-to-apples.

Usage
-----
python experiments/sketchrefine_scalability/run_sketchrefine_scalability.py \\
    --data_path    data/data_ctm.csv \\
    --shared_docs  data/shared_docs/ \\
    --users_path   data/user_summary_jsons/ \\
    --results_path results/SketchRefine/

Run with the InfoSecurity conda env (docplex + cplex + sentence-transformers):
    /Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python
"""

import argparse
import csv
import logging
import os
import pickle
import random
import sys
import warnings
from timeit import default_timer as timer

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.data_reader import UserDataReader
from utils.evaluation import EvaluationScore
from models.ex2bundle import Ex2Bundle

METHODS = ("direct", "sketch_refine")
BINS = ("small", "medium", "large")


def build_instances(udr, num_examples, num_test, limit=None):
    """Precompute identical train/test splits shared by every method.

    Returns a list of dicts: intent_idx, intent_text, example_set, target,
    gt_text, gt_indices.
    """
    ground_truth, gt_indices = udr.read_summaries_list()
    intent_doc = udr.read_intent_doc()
    sudocu_data = udr.read_example_summaries_sudocu()

    instances = []
    for i, intent in enumerate(intent_doc):
        exsum = sudocu_data[i]
        n = len(exsum)
        if n < num_examples + 1:
            continue
        intent_text = list(intent.keys())[0]
        documents = list(intent.values())[0]

        train_split = random.sample(range(n), num_examples)
        test_indices = [idx for idx in range(n) if idx not in train_split][:num_test]
        example_set = [exsum[t] for t in train_split]

        for t in test_indices:
            instances.append({
                "intent_idx":  i,
                "intent_text": intent_text,
                "example_set": example_set,
                "target":      documents[t],
                "gt_text":     ground_truth[i][t],
                "gt_indices":  gt_indices[i][t],
            })
    if limit:
        instances = instances[:limit]
    return instances


def size_bin(avg_len, thresholds):
    lo, hi = thresholds
    if avg_len <= lo:
        return "small"
    if avg_len <= hi:
        return "medium"
    return "large"


def run_all(instances, args, scorer):
    """Run both methods over every instance; return per-instance records.

    One shared model instance is used for both methods, so `avg_len` (and
    hence bounds and candidate pool) is identical between the direct/
    sketch_refine pair for a given instance.
    """
    model = Ex2Bundle(
        args.data_path, args.shared_docs, args.n_topics, args.num_examples,
        is_generative=False,
        sketch_refine_size_threshold=args.sketch_refine_size_threshold,
        sketch_refine_radius_limit=args.sketch_refine_radius_limit,
        max_repeat_cap=args.max_repeat_cap,
        sketch_refine_timelimit=args.sketch_refine_timelimit,
    )

    avg_lens = [model.get_avg_summaries_length(inst["example_set"]) for inst in instances]
    thresholds = (
        float(np.percentile(avg_lens, 33.3)) if avg_lens else 0.0,
        float(np.percentile(avg_lens, 66.7)) if avg_lens else 0.0,
    )

    records = []
    for k, (inst, avg_len) in enumerate(zip(instances, avg_lens)):
        if k % 25 == 0:
            logging.info("%d/%d", k, len(instances))
        bin_label = size_bin(avg_len, thresholds)

        for method in args.methods:
            try:
                t0 = timer()
                pred, learn_t, ilp_t, slen, relax_freq, num_relaxed = model.get_predicted_summary(
                    inst["target"], inst["example_set"],
                    do_sketch_refine=(method == "sketch_refine"),
                )
                wall = timer() - t0
            except Exception as e:
                logging.warning("[%s] skip %s: %s", method, inst["target"], e)
                continue

            if pred.startswith("def_sum"):
                logging.warning("[%s] error state on %s", method, inst["target"])
                continue

            rouge = scorer.compareScore(pred, inst["gt_text"])          # [[p,r,f1,f2] x3]
            sbert = scorer.compare_summaries_sbert(pred, inst["gt_text"])

            records.append({
                "method":       method,
                "size_bin":     bin_label,
                "avg_len":      avg_len,
                "intent_idx":   inst["intent_idx"],
                "target":       inst["target"],
                "runtime_wall": wall,
                "learn_time":   learn_t,
                "ilp_time":     ilp_t,
                "summary_len":  slen,
                "sbert":        sbert,
                "rouge1_f1":    rouge[0][2],
                "rouge2_f1":    rouge[1][2],
                "rougeL_f1":    rouge[2][2],
                "relax_freq":   relax_freq,
                "num_relaxed":  num_relaxed,
            })
    return records


def _mean(records, key):
    vals = [r[key] for r in records]
    return float(np.mean(vals)) if vals else float("nan")


def summarize(records):
    """Build the comparison table, one row per (size_bin, method)."""
    header = ["size_bin", "method", "n", "avg_len", "runtime_s", "learn_s", "ilp_s",
              "summary_len", "sbert", "rouge1", "rouge2", "rougeL", "relax_freq"]
    rows = []
    for bin_label in BINS:
        for method in METHODS:
            recs = [r for r in records if r["size_bin"] == bin_label and r["method"] == method]
            if not recs:
                continue
            rows.append([
                bin_label, method, len(recs),
                round(_mean(recs, "avg_len"), 2),
                round(_mean(recs, "runtime_wall"), 4),
                round(_mean(recs, "learn_time"), 4),
                round(_mean(recs, "ilp_time"), 4),
                round(_mean(recs, "summary_len"), 2),
                round(_mean(recs, "sbert"), 4),
                round(_mean(recs, "rouge1_f1"), 4),
                round(_mean(recs, "rouge2_f1"), 4),
                round(_mean(recs, "rougeL_f1"), 4),
                round(_mean(recs, "relax_freq"), 4),
            ])
    return header, rows


def _print_table(header, rows):
    if not rows:
        print("(no rows)")
        return
    widths = [max(len(str(header[c])), *(len(str(r[c])) for r in rows)) for c in range(len(header))]
    line = "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header)))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))


def plot_runtime(header, rows, results_path):
    fig, ax = plt.subplots(figsize=(6, 4.2))
    bin_x = {b: i for i, b in enumerate(BINS)}
    for method, color in zip(METHODS, ("tab:blue", "tab:orange")):
        xs, ys = [], []
        for row in rows:
            row = dict(zip(header, row))
            if row["method"] != method:
                continue
            xs.append(bin_x[row["size_bin"]])
            ys.append(row["runtime_s"])
        if xs:
            order = np.argsort(xs)
            xs, ys = np.array(xs)[order], np.array(ys)[order]
            ax.plot(xs, ys, "o-", color=color, label=method)
    ax.set_xticks(list(bin_x.values()))
    ax.set_xticklabels(list(bin_x.keys()))
    ax.set_xlabel("Candidate-pool size bin (avg_len tercile)")
    ax.set_ylabel("Mean wall-clock runtime (s)")
    ax.set_title("DIRECT vs SKETCH-REFINE runtime")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    out = os.path.join(results_path, "fig_sketchrefine_runtime.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logging.info("Saved %s", out)


def main():
    parser = argparse.ArgumentParser(description="SketchRefine scalability: DIRECT vs SKETCH-REFINE")
    parser.add_argument("--data_path",    required=True)
    parser.add_argument("--shared_docs",  required=True)
    parser.add_argument("--users_path",   required=True)
    parser.add_argument("--results_path", default="results/SketchRefine")
    parser.add_argument("--num_examples", type=int, default=5)
    parser.add_argument("--num_test",     type=int, default=3)
    parser.add_argument("--n_topics",     type=int, default=10)
    parser.add_argument("--min_range",    type=int, default=0)
    parser.add_argument("--max_index",    type=int, default=275)
    parser.add_argument("--methods", nargs="+", default=list(METHODS), choices=list(METHODS))
    parser.add_argument("--sketch_refine_size_threshold", type=int, default=20)
    parser.add_argument("--sketch_refine_radius_limit",   type=float, default=None)
    parser.add_argument("--max_repeat_cap",               type=int, default=None)
    parser.add_argument("--sketch_refine_timelimit",      type=float, default=60)
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap #instances (quick smoke runs)")
    parser.add_argument("--seed", type=int, default=7891)
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    os.makedirs(args.results_path, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    random.seed(args.seed)
    udr = UserDataReader(args.users_path, args.data_path, args.min_range, args.max_index)
    instances = build_instances(udr, args.num_examples, args.num_test, args.limit)
    logging.info("Built %d evaluation instances (5 source / 3 target per intent)",
                 len(instances))

    scorer = EvaluationScore(args.shared_docs, args.data_path, args.n_topics)

    pkl_path = os.path.join(args.results_path, "sketchrefine_records.pkl")
    if os.path.exists(pkl_path):
        logging.info("Found existing %s; re-running overwrites it (no per-cell resume "
                     "in this script, unlike item6_bound_direction's grid sweep).", pkl_path)

    records = run_all(instances, args, scorer)
    with open(pkl_path, "wb") as f:
        pickle.dump(records, f)

    header, rows = summarize(records)
    with open(os.path.join(args.results_path, "sketchrefine_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    print("\n=== DIRECT vs SKETCH-REFINE, by candidate-pool size ===")
    _print_table(header, rows)
    if rows:
        plot_runtime(header, rows, args.results_path)
    logging.info("Saved records + summary to %s", args.results_path)


if __name__ == "__main__":
    main()
