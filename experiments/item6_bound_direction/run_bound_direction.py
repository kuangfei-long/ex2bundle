"""
Revision Item 6: Bound-direction comparison (Meta-1 / R3.O2 / R3.D2).

Compares three bound-relaxation strategies on the SubSumE dataset under the
RQ2 setting (5 source / 3 target summaries per intent):

  symmetric    Current algorithm  -- ConflictRefiner (IIS) finds the violated
                                      topics, then BOTH bound sides are widened.
  directional  IIS + directional  -- same IIS, but only the violated side moves.
  feasopt      CPLEX FeasOpt      -- one-shot minimal total bound relaxation.

For every (mode, instance) we record the columns of the Item-6 table:
  Runtime, Semantic similarity (SBERT), ROUGE-1/2/L, initial bound width,
  relaxed bound width, bound-shift distance, and the number of relaxations.

All three modes are evaluated on the *identical* train/test splits so the
comparison is apples-to-apples.

Usage
-----
python experiments/item6_bound_direction/run_bound_direction.py \\
    --data_path    data/data_ctm.csv \\
    --shared_docs  data/shared_docs/ \\
    --users_path   data/user_summary_jsons/ \\
    --results_path results/Item6/

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

from utils.data_reader import UserDataReader
from utils.evaluation import EvaluationScore
from models.ex2bundle import Ex2Bundle, VALID_RELAXATION_MODES

MODES = ("symmetric", "directional", "feasopt")


def build_instances(udr, num_examples, num_test, limit=None):
    """Precompute identical train/test splits shared by every mode.

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


def run_mode(mode, instances, args, scorer, bound_pad):
    """Run one relaxation mode over all instances; return per-instance records."""
    model = Ex2Bundle(
        args.data_path, args.shared_docs, args.n_topics, args.num_examples,
        is_generative=False, relaxation_mode=mode, bound_pad=bound_pad,
    )
    records = []
    for k, inst in enumerate(instances):
        if k % 25 == 0:
            logging.info("[%s] %d/%d", mode, k, len(instances))
        try:
            t0 = timer()
            pred, learn_t, ilp_t, slen, relax_freq, num_relaxed = \
                model.get_predicted_summary(inst["target"], inst["example_set"])
            wall = timer() - t0
        except Exception as e:
            logging.warning("[%s] skip %s: %s", mode, inst["target"], e)
            continue

        if pred.startswith("def_sum"):
            logging.warning("[%s] error state on %s", mode, inst["target"])
            continue

        rouge = scorer.compareScore(pred, inst["gt_text"])          # [[p,r,f1,f2] x3]
        sbert = scorer.compare_summaries_sbert(pred, inst["gt_text"])

        init_w = float(np.mean(model.initial_bounds[:, 1] - model.initial_bounds[:, 0]))
        relax_w = float(np.mean(model.utilized_bounds[:, 1] - model.utilized_bounds[:, 0]))

        records.append({
            "bound_pad":    bound_pad,
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
            "rouge_full":   rouge,
            "relax_freq":   relax_freq,
            "num_relaxed":  num_relaxed,
            "init_width":   init_w,
            "relaxed_width": relax_w,
            "bound_shift":  model.last_relax_magnitude,
        })
    return records


def _mean(records, key):
    vals = [r[key] for r in records]
    return float(np.mean(vals)) if vals else float("nan")


def _relax_rate(recs):
    """Fraction of instances that triggered at least one relaxation round."""
    if not recs:
        return float("nan")
    return sum(1 for r in recs if r["relax_freq"] > 0) / len(recs)


def summarize(all_records, conditional=False):
    """Build the Item-6 comparison table, one row per (bound_pad, mode).

    conditional=True restricts each row to the instances that actually relaxed
    (relax_freq > 0) for that bound_pad, so the bound-shift signal is not
    diluted by the always-feasible majority.
    """
    header = ["bound_pad", "mode", "n", "relax_rate", "runtime_s", "sbert",
              "rouge1", "rouge2", "rougeL", "init_width", "relaxed_width",
              "bound_shift", "relax_freq", "num_relaxed"]
    rows = []
    for pad in sorted(all_records.keys(), reverse=True):
        per_mode = all_records[pad]
        for mode in MODES:
            recs = per_mode.get(mode, [])
            if not recs:
                continue
            full_n = len(recs)
            rate = _relax_rate(recs)
            if conditional:
                recs = [r for r in recs if r["relax_freq"] > 0]
                if not recs:
                    continue
            rows.append([
                pad, mode, len(recs), round(rate, 4),
                round(_mean(recs, "runtime_wall"), 4),
                round(_mean(recs, "sbert"), 4),
                round(_mean(recs, "rouge1_f1"), 4),
                round(_mean(recs, "rouge2_f1"), 4),
                round(_mean(recs, "rougeL_f1"), 4),
                round(_mean(recs, "init_width"), 4),
                round(_mean(recs, "relaxed_width"), 4),
                round(_mean(recs, "bound_shift"), 4),
                round(_mean(recs, "relax_freq"), 4),
                round(_mean(recs, "num_relaxed"), 4),
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


def main():
    parser = argparse.ArgumentParser(description="Item 6: bound-direction comparison")
    parser.add_argument("--data_path",    required=True)
    parser.add_argument("--shared_docs",  required=True)
    parser.add_argument("--users_path",   required=True)
    parser.add_argument("--results_path", default="results/Item6/sweep")
    parser.add_argument("--num_examples", type=int, default=5)
    parser.add_argument("--num_test",     type=int, default=3)
    parser.add_argument("--n_topics",     type=int, default=10)
    parser.add_argument("--min_range",    type=int, default=0)
    parser.add_argument("--max_index",    type=int, default=275)
    parser.add_argument("--modes", nargs="+", default=list(MODES), choices=list(MODES))
    parser.add_argument("--bound_pads", nargs="+", type=float, default=[0.1],
                        help="Bound-padding factors to sweep. 0.1 = paper default; "
                             "negative tightens bounds inward to force more relaxation.")
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

    for m in args.modes:
        assert m in VALID_RELAXATION_MODES

    random.seed(args.seed)
    udr = UserDataReader(args.users_path, args.data_path, args.min_range, args.max_index)
    instances = build_instances(udr, args.num_examples, args.num_test, args.limit)
    logging.info("Built %d evaluation instances (5 source / 3 target per intent)",
                 len(instances))

    scorer = EvaluationScore(args.shared_docs, args.data_path, args.n_topics)

    # all_records[bound_pad][mode] = list of per-instance records.
    # Checkpoint after every (pad, mode) cell so a killed run (e.g. laptop
    # sleep) keeps completed work and can be resumed by re-running the same
    # command — finished cells are detected and skipped.
    pkl_path = os.path.join(args.results_path, "item6_records.pkl")
    all_records = {}
    if os.path.exists(pkl_path):
        try:
            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)
            # Only resume if it's the sweep format {pad: {mode: [...]}}.
            if loaded and all(isinstance(v, dict) for v in loaded.values()):
                all_records = loaded
                logging.info("Resuming from checkpoint %s", pkl_path)
        except Exception as e:
            logging.warning("Could not load checkpoint (%s); starting fresh", e)

    for pad in args.bound_pads:
        all_records.setdefault(pad, {})
        for mode in args.modes:
            if all_records[pad].get(mode):
                logging.info("=== bound_pad=%s  mode=%s  (cached, skip) ===", pad, mode)
                continue
            logging.info("=== bound_pad=%s  mode=%s ===", pad, mode)
            all_records[pad][mode] = run_mode(mode, instances, args, scorer, pad)
            with open(pkl_path, "wb") as f:      # checkpoint this cell
                pickle.dump(all_records, f)
            logging.info("checkpoint saved after bound_pad=%s mode=%s", pad, mode)

    header, rows = summarize(all_records, conditional=False)
    with open(os.path.join(args.results_path, "item6_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    cheader, crows = summarize(all_records, conditional=True)
    with open(os.path.join(args.results_path, "item6_summary_relaxed_only.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cheader)
        w.writerows(crows)

    print("\n=== All instances ===")
    _print_table(header, rows)
    print("\n=== Relaxation-triggering instances only ===")
    _print_table(cheader, crows)
    logging.info("Saved records + summaries to %s", args.results_path)


if __name__ == "__main__":
    main()
