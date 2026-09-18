"""
One-shot Item-6 report: quality/relaxation metrics + clean runtime, per
(bound_pad, mode), in a single pass over a single set of instances.

  - bound_pad: Ex2Bundle.get_predicted_summary(bounds=...) already accepts a
    pre-computed bounds array; SuDocuBase.get_bounds(bound_pad=...) (which
    Ex2Bundle inherits unchanged) still supports the pad. So pads are swept
    here by computing bounds externally and passing them in explicitly.
  - relaxation_mode: Ex2Bundle's DIRECT solve loop dispatches its relaxation
    step through two `self.`-resolved hooks, _identify_violated_constraints
    and _relax_violated_bounds. Subclassing Ex2Bundle here and overriding
    just those two hooks reproduces "directional" and "feasopt" without
    editing the base class at all; "symmetric" is the unmodified base class.

Consolidates what run_bound_direction.py and bench_runtime.py each do
separately:
  - quality/relaxation: relax_rate, rouge1/2/L, sbert, bound_shift,
    relax_freq, num_relaxed -- mean over ALL instances in the cell.
  - clean runtime: median/mean solve time on the INFEASIBLE subset only,
    timed back-to-back in-process with `--repeats` samples per instance
    (bench_runtime.py's method), no round-binning.

Usage as a library
-------------------
    from experiments.item6_bound_direction.full_report import (
        run_full_item6_report, print_full_item6_report,
    )
    report = run_full_item6_report(
        data_path="data/data_ctm.csv", shared_docs="data/shared_docs/",
        users_path="data/user_summary_jsons/",
        bound_pads=[0.1, -0.2, -0.3, -0.4, -0.5, -0.6],
        limit=15, repeats=2,
    )
    print_full_item6_report(report)

Usage from the CLI
------------------
    python experiments/item6_bound_direction/full_report.py \\
        --data_path data/data_ctm.csv --shared_docs data/shared_docs/ \\
        --users_path data/user_summary_jsons/ --limit 15 --repeats 2
"""

import argparse
import random
import sys
import os
import time
import warnings
from collections import defaultdict

import numpy as np
from docplex.mp.conflict_refiner import ConflictRefiner
from docplex.mp.relaxer import Relaxer

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root

from utils.data_reader import UserDataReader
from utils.evaluation import EvaluationScore
from models.ex2bundle import Ex2Bundle

MODES = ("symmetric", "directional", "feasopt")


class _DirectionalEx2Bundle(Ex2Bundle):
    """Same DIRECT solve loop as Ex2Bundle, but widens only the violated
    SIDE of each flagged topic constraint (base class widens both sides).
    Overrides only the two relaxation hooks the loop calls by `self.`
    dispatch -- models/ex2bundle.py is not touched."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sides = {}  # {topic_idx: 'min'|'max'|'both'} for the pending round

    def _identify_violated_constraints(self, opt_model, bounds, prev_relax_topics):
        relax, sides, round_relaxed = set(), {}, False
        if self.use_conflict_refiner:
            try:
                cr_res = ConflictRefiner().refine_conflict(opt_model, display=False)
                for conflict in cr_res.iter_conflicts():
                    name = str(conflict[0]).split(":")[0].strip()
                    for side, prefix in (("min", "constraint_min_topic"), ("max", "constraint_max_topic")):
                        if name.startswith(prefix):
                            j = int(name[len(prefix):])
                            relax.add(j)
                            sides[j] = side
                            round_relaxed = True
            except Exception:
                pass
        if not relax:
            # Fallback: no direction known, widen both sides (degenerates to symmetric).
            bound_diffs = np.abs(np.array(bounds)[:, 1:2] - np.array(bounds)[:, 0:1]).squeeze()
            avg_diff = np.mean(bound_diffs)
            for i in range(self.nTopics):
                if np.abs(bound_diffs[i]) < avg_diff:
                    relax.add(i)
                    sides[i] = "both"
                    round_relaxed = True
        self._sides = sides
        return list(relax), round_relaxed

    def _relax_violated_bounds(self, model, bounds, step_sizes, relax_topics, solv_ctr, step_mult):
        for j in range(self.nTopics):
            if (j in np.array(relax_topics)) and solv_ctr > 0:
                side = self._sides.get(j, "both")
                if side in ("min", "both"):
                    lb_new = bounds[j][0] - step_mult * step_sizes[j]
                    bounds[j][0] = lb_new if lb_new > 0 else 0.0
                if side in ("max", "both"):
                    bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]
            model.get_constraint_by_name("constraint_min_topic{0}".format(j)).rhs = bounds[j][0]
            model.get_constraint_by_name("constraint_max_topic{0}".format(j)).rhs = bounds[j][1]


class _FeasoptEx2Bundle(Ex2Bundle):
    """Same DIRECT solve loop as Ex2Bundle, but on the first infeasible
    round relaxes ALL violated constraints at once by CPLEX FeasOpt's
    minimal-total-slack amounts (base class widens step-by-step,
    iteratively). Overrides only the two relaxation hooks -- models/
    ex2bundle.py is not touched."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._deltas = {}  # {(topic_idx, 'min'|'max'): signed_rhs_delta}

    def _identify_violated_constraints(self, opt_model, bounds, prev_relax_topics):
        try:
            relaxer = Relaxer()
            relaxer.relax(opt_model)
        except Exception:
            return list(prev_relax_topics), False

        deltas = {}
        for ct, amount in relaxer.iter_relaxations():
            if amount == 0:
                continue
            name = str(getattr(ct, "name", None) or ct).split(":")[0].strip()
            for side, prefix in (("min", "constraint_min_topic"), ("max", "constraint_max_topic")):
                if name.startswith(prefix):
                    deltas[(int(name[len(prefix):]), side)] = amount
        self._deltas = deltas
        return sorted({j for (j, _side) in deltas}), bool(deltas)

    def _relax_violated_bounds(self, model, bounds, step_sizes, relax_topics, solv_ctr, step_mult):
        for (j, side), amount in self._deltas.items():
            if side == "min":
                lb_new = bounds[j][0] + amount
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
            else:
                bounds[j][1] = bounds[j][1] + amount
        self._deltas = {}
        for j in range(self.nTopics):
            model.get_constraint_by_name("constraint_min_topic{0}".format(j)).rhs = bounds[j][0]
            model.get_constraint_by_name("constraint_max_topic{0}".format(j)).rhs = bounds[j][1]


_MODEL_CLASSES = {"symmetric": Ex2Bundle, "directional": _DirectionalEx2Bundle, "feasopt": _FeasoptEx2Bundle}


def _build_instances(udr, num_examples, num_test, limit=None):
    ground_truth, _gt_indices = udr.read_summaries_list()
    intent_doc = udr.read_intent_doc()
    sudocu_data = udr.read_example_summaries_sudocu()

    instances = []
    for i, intent in enumerate(intent_doc):
        exsum = sudocu_data[i]
        n = len(exsum)
        if n < num_examples + 1:
            continue
        documents = list(intent.values())[0]
        train_split = random.sample(range(n), num_examples)
        test_indices = [idx for idx in range(n) if idx not in train_split][:num_test]
        example_set = [exsum[t] for t in train_split]
        for t in test_indices:
            instances.append({
                "intent_idx": i,
                "target": documents[t],
                "example_set": example_set,
                "gt_text": ground_truth[i][t],
            })
    if limit:
        instances = instances[:limit]
    return instances


def run_full_item6_report(data_path, shared_docs, users_path,
                           bound_pads=(0.1, -0.2, -0.3, -0.4, -0.5, -0.6),
                           modes=MODES, num_examples=5, num_test=3, n_topics=10,
                           limit=15, repeats=2, seed=7891):
    """Run the Item-6 bound-direction comparison across `bound_pads` x `modes`.

    Returns
    -------
    dict:
      "quality": {bound_pad: {mode: {n, relax_rate, rouge1_f1, rouge2_f1,
                                      rougeL_f1, sbert, bound_shift,
                                      relax_freq, num_relaxed}}}
      "runtime": {bound_pad: {mode: {n_infeasible_timed, median_s, mean_s}}}
      "n_instances", "bound_pads", "modes"
    """
    for m in modes:
        assert m in _MODEL_CLASSES, f"unknown mode {m}"

    random.seed(seed)
    udr = UserDataReader(users_path, data_path, 0, 275)
    instances = _build_instances(udr, num_examples, num_test, limit)
    scorer = EvaluationScore(shared_docs, data_path, n_topics)

    quality, runtime = {}, {}

    for pad in bound_pads:
        models = {m: _MODEL_CLASSES[m](data_path, shared_docs, n_topics, num_examples,
                                        is_generative=False)
                  for m in modes}

        per_mode_records = {m: [] for m in modes}
        per_mode_medians = {m: [] for m in modes}  # one median-over-repeats per infeasible instance

        for inst in instances:
            # Same padded bounds handed to all 3 modes for this instance, so the
            # comparison is apples-to-apples (get_bounds is unchanged/inherited).
            base_bounds, _avg_len = models[modes[0]].get_bounds(inst["example_set"], bound_pad=pad)
            base_bounds = np.array(base_bounds, dtype=float)

            for m in modes:
                try:
                    pred, _learn_t, _ilp_t, _slen, relax_freq, num_relaxed = \
                        models[m].get_predicted_summary(inst["target"], inst["example_set"],
                                                          bounds=base_bounds.copy())
                except Exception:
                    continue
                if pred.startswith("def_sum"):
                    continue

                rouge = scorer.compareScore(pred, inst["gt_text"])          # [[p,r,f1,f2] x3]
                sbert = scorer.compare_summaries_sbert(pred, inst["gt_text"])
                bound_shift = float(np.sum(np.abs(models[m].utilized_bounds - base_bounds)))
                per_mode_records[m].append({
                    "rouge1_f1": rouge[0][2], "rouge2_f1": rouge[1][2], "rougeL_f1": rouge[2][2],
                    "sbert": sbert, "relax_freq": relax_freq, "num_relaxed": num_relaxed,
                    "bound_shift": bound_shift,
                })

                if relax_freq > 0:
                    # Clean back-to-back timing (bench_runtime.py's method), median of `repeats`.
                    times = []
                    for _ in range(repeats):
                        t0 = time.perf_counter()
                        models[m].get_predicted_summary(inst["target"], inst["example_set"],
                                                          bounds=base_bounds.copy())
                        times.append(time.perf_counter() - t0)
                    per_mode_medians[m].append(float(np.median(times)))

        quality[pad], runtime[pad] = {}, {}
        for m in modes:
            recs = per_mode_records[m]
            n = len(recs)
            quality[pad][m] = {
                "n": n,
                "relax_rate": (sum(1 for r in recs if r["relax_freq"] > 0) / n) if n else float("nan"),
                "rouge1_f1":  float(np.mean([r["rouge1_f1"] for r in recs])) if recs else float("nan"),
                "rouge2_f1":  float(np.mean([r["rouge2_f1"] for r in recs])) if recs else float("nan"),
                "rougeL_f1":  float(np.mean([r["rougeL_f1"] for r in recs])) if recs else float("nan"),
                "sbert":      float(np.mean([r["sbert"] for r in recs])) if recs else float("nan"),
                "bound_shift": float(np.mean([r["bound_shift"] for r in recs])) if recs else float("nan"),
                "relax_freq": float(np.mean([r["relax_freq"] for r in recs])) if recs else float("nan"),
                "num_relaxed": float(np.mean([r["num_relaxed"] for r in recs])) if recs else float("nan"),
            }
            medians = per_mode_medians[m]
            runtime[pad][m] = {
                "n_infeasible_timed": len(medians),
                "median_s": float(np.median(medians)) if medians else float("nan"),
                "mean_s":   float(np.mean(medians)) if medians else float("nan"),
            }

    return {
        "quality": quality, "runtime": runtime,
        "n_instances": len(instances), "bound_pads": list(bound_pads), "modes": list(modes),
    }


def print_full_item6_report(report):
    modes = report["modes"]

    def _print(title, table, cols):
        print(f"=== {title} ===")
        header = ["bound_pad"] + [f"{m[:3]}_{c}" for m in modes for c in cols]
        widths = [max(len(h), 8) for h in header]
        print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
        print("-" * (sum(widths) + 2 * (len(widths) - 1)))
        for pad in report["bound_pads"]:
            row = [str(pad)]
            for m in modes:
                cell = table[pad][m]
                for c in cols:
                    v = cell[c]
                    if isinstance(v, float):
                        row.append(f"{v:.4f}" if not np.isnan(v) else "-")
                    else:
                        row.append(str(v))
            print("  ".join(c.ljust(w) for c, w in zip(row, widths)))
        print()

    _print("Quality / relaxation (mean over all instances)", report["quality"],
            ["n", "relax_rate", "rouge1_f1", "sbert", "bound_shift", "num_relaxed"])
    _print("Clean runtime, infeasible instances only (median of repeats)", report["runtime"],
            ["n_infeasible_timed", "median_s", "mean_s"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data_path", required=True)
    ap.add_argument("--shared_docs", required=True)
    ap.add_argument("--users_path", required=True)
    ap.add_argument("--bound_pads", nargs="+", type=float, default=[0.1, -0.2, -0.3, -0.4, -0.5, -0.6])
    ap.add_argument("--modes", nargs="+", default=list(MODES), choices=list(MODES))
    ap.add_argument("--num_examples", type=int, default=5)
    ap.add_argument("--num_test", type=int, default=3)
    ap.add_argument("--n_topics", type=int, default=10)
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--seed", type=int, default=7891)
    args = ap.parse_args()

    report = run_full_item6_report(
        args.data_path, args.shared_docs, args.users_path,
        bound_pads=args.bound_pads, modes=args.modes,
        num_examples=args.num_examples, num_test=args.num_test, n_topics=args.n_topics,
        limit=args.limit, repeats=args.repeats, seed=args.seed,
    )
    print_full_item6_report(report)


if __name__ == "__main__":
    main()