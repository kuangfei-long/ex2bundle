"""
One-shot Item-6 report: quality/relaxation metrics + clean runtime, per
(bound_pad, mode), in a single pass over a single set of instances.

models/ex2bundle.py dropped relaxation_mode/bound_pad support in the
Section-4.5 refactor. This module restores the three Item-6 strategies
without touching that file: bound_pad is applied by computing bounds
externally via SuDocuBase.get_bounds(bound_pad=...) and passing them in;
relaxation_mode is applied by subclassing Ex2Bundle and overriding its two
relaxation hooks (_identify_violated_constraints, _relax_violated_bounds)
for "directional"/"feasopt" -- "symmetric" is the unmodified base class.

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
import contextlib
import csv
import random
import sys
import os
import time
import warnings
from collections import defaultdict
from unittest.mock import patch

import numpy as np
import docplex.mp.model as cpx
from docplex.mp.conflict_refiner import ConflictRefiner
from docplex.mp.relaxer import Relaxer

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # repo root

from utils.data_reader import UserDataReader
from utils.evaluation import EvaluationScore
from models.ex2bundle import Ex2Bundle

MODES = ("symmetric", "directional", "feasopt")


class _ObjectiveCaptureModel(cpx.Model):
    """Drop-in for cpx.Model, active only during one get_predicted_summary()
    call (see _capture_objective). models/ex2bundle.py never exposes the
    solution object from .solve() -- this subclass records each solve's
    objective into a shared sink instead of modifying that file.

    _FeasoptEx2Bundle's one-shot shortcut replaces .solve() directly and
    bypasses this override, so it writes to the sink itself."""

    _sink = None  # {"value": float|None}, set by _capture_objective while active

    def solve(self, *args, **kwargs):
        sol = super().solve(*args, **kwargs)
        if sol is not None and _ObjectiveCaptureModel._sink is not None:
            _ObjectiveCaptureModel._sink["value"] = sol.objective_value
        return sol


@contextlib.contextmanager
def _capture_objective():
    """Yields a {"value": float|None} sink holding the objective of the
    solution get_predicted_summary() ends up returning, captured without
    touching models/ex2bundle.py (see _ObjectiveCaptureModel)."""
    sink = {"value": None}
    _ObjectiveCaptureModel._sink = sink
    with patch("docplex.mp.model.Model", _ObjectiveCaptureModel):
        try:
            yield sink
        finally:
            _ObjectiveCaptureModel._sink = None


class _DirectionalEx2Bundle(Ex2Bundle):
    """Same solve loop as Ex2Bundle, but widens only the violated SIDE of
    each flagged topic (base class widens both). Overrides only the two
    relaxation hooks -- models/ex2bundle.py is untouched."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sides = {}  # {topic_idx: set of 'min'/'max' flagged this round}

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
                            # Both sides of one topic can be flagged in the same round -- keep both.
                            sides.setdefault(j, set()).add(side)
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
                    sides[i] = {"min", "max"}
                    round_relaxed = True
        self._sides = sides
        return list(relax), round_relaxed

    def _relax_violated_bounds(self, model, bounds, step_sizes, relax_topics, solv_ctr, step_mult):
        for j in range(self.nTopics):
            if (j in np.array(relax_topics)) and solv_ctr > 0:
                sides = self._sides.get(j, {"min", "max"})
                if "min" in sides:
                    lb_new = bounds[j][0] - step_mult * step_sizes[j]
                    bounds[j][0] = lb_new if lb_new > 0 else 0.0
                if "max" in sides:
                    bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]
            model.get_constraint_by_name("constraint_min_topic{0}".format(j)).rhs = bounds[j][0]
            model.get_constraint_by_name("constraint_max_topic{0}".format(j)).rhs = bounds[j][1]


class _FeasoptEx2Bundle(Ex2Bundle):
    """Same solve loop as Ex2Bundle, but the first infeasible round is
    resolved by one CPLEX FeasOpt call (Relaxer's OptSum mode already
    re-optimizes the real objective under its minimal relaxation), and that
    solution is used directly -- matching the original one-shot design.
    _relax_violated_bounds shortcuts the loop's next solve() to hand back
    that cached solution instead of a redundant resolve. Overrides only the
    two relaxation hooks -- models/ex2bundle.py is untouched."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._deltas = {}          # {(topic_idx, 'min'|'max'): signed_rhs_delta}
        self._relaxed_solution = None  # Relaxer's own solution, pending hand-off

    def _identify_violated_constraints(self, opt_model, bounds, prev_relax_topics):
        # self is the only channel to _relax_violated_bounds -- clear stale
        # state up front so a prior instance's unconsumed solution can't leak in.
        self._deltas = {}
        self._relaxed_solution = None
        try:
            relaxer = Relaxer()
            relaxed_sol = relaxer.relax(opt_model)
        except Exception:
            return list(prev_relax_topics), False
        if relaxed_sol is None:
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
        self._relaxed_solution = relaxed_sol
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

        if self._relaxed_solution is not None:
            cached_solution = self._relaxed_solution
            self._relaxed_solution = None
            model.solve = lambda *_a, **_kw: cached_solution
            # Bypasses _ObjectiveCaptureModel.solve()'s override -- record here instead.
            if _ObjectiveCaptureModel._sink is not None:
                _ObjectiveCaptureModel._sink["value"] = cached_solution.objective_value


_MODEL_CLASSES = {"symmetric": Ex2Bundle, "directional": _DirectionalEx2Bundle, "feasopt": _FeasoptEx2Bundle}

_QUALITY_KEYS = ("rouge1_f1", "rouge2_f1", "rougeL_f1", "sbert", "bound_shift", "num_relaxed", "objective")


def _mean_stats(recs, keys=_QUALITY_KEYS):
    """{n, key: mean(key over recs)} for each key, nan when recs is empty."""
    stats = {"n": len(recs)}
    for k in keys:
        stats[k] = float(np.mean([r[k] for r in recs])) if recs else float("nan")
    return stats


_PAIRWISE_PLACEHOLDER = {
    "n_infeasible_paired": "-",
    "objective_win_rate": "-", "objective_tie_rate": "-", "objective_avg_diff": float("nan"),
    "runtime_win_rate": "-", "runtime_tie_rate": "-",
    "runtime_avg_diff": float("nan"), "runtime_median_diff": float("nan"),
}


def _pairwise_vs_baseline(raw_rows, pad, modes, baseline="symmetric", tol=1e-6):
    """Pairwise directional-vs-symmetric / feasopt-vs-symmetric comparison
    for this bound_pad, restricted to queries that actually required
    relaxation under BOTH sides (relax_freq > 0 for the baseline AND for
    the compared mode on that same instance) -- the two modes only
    diverge once relaxation kicks in, and clean_median_time_s is only
    ever measured on that infeasible subset to begin with, so anything
    still feasible outright is dropped from every stat below.

    Objective is "higher is better" (win = strictly beats baseline);
    runtime is "lower is better" (win = strictly faster than baseline).
    Ties use `tol` on the raw difference. Keyed by (intent_idx, target)
    rather than list position, so it's safe even if a mode dropped an
    instance the others kept (e.g. a "def_sum" fallback skip).

    Returns {mode: {n_infeasible_paired, objective_win_rate, objective_tie_rate,
                     objective_avg_diff, runtime_win_rate, runtime_tie_rate,
                     runtime_avg_diff, runtime_median_diff}} for every mode in
    `modes`; the baseline mode itself maps to _PAIRWISE_PLACEHOLDER (not
    compared against itself)."""
    by_instance = defaultdict(dict)
    for r in raw_rows:
        if r["bound_pad"] == pad and r["mode"] in modes:
            by_instance[(r["intent_idx"], r["target"])][r["mode"]] = r

    others = [m for m in modes if m != baseline]
    obj_win = {m: 0 for m in others}
    obj_tie = {m: 0 for m in others}
    obj_diffs = {m: [] for m in others}
    rt_win = {m: 0 for m in others}
    rt_tie = {m: 0 for m in others}
    rt_diffs = {m: [] for m in others}
    n_paired = {m: 0 for m in others}

    for recs in by_instance.values():
        base_r = recs.get(baseline)
        if base_r is None or base_r["relax_freq"] <= 0:
            continue
        for m in others:
            r = recs.get(m)
            if r is None or r["relax_freq"] <= 0:
                continue
            n_paired[m] += 1

            d_obj = r["objective"] - base_r["objective"]
            obj_diffs[m].append(d_obj)
            if d_obj > tol:
                obj_win[m] += 1
            elif abs(d_obj) <= tol:
                obj_tie[m] += 1

            d_rt = r["clean_median_time_s"] - base_r["clean_median_time_s"]
            rt_diffs[m].append(d_rt)
            if d_rt < -tol:
                rt_win[m] += 1
            elif abs(d_rt) <= tol:
                rt_tie[m] += 1

    result = {baseline: dict(_PAIRWISE_PLACEHOLDER)}
    for m in others:
        n = n_paired[m]
        if n == 0:
            result[m] = {**_PAIRWISE_PLACEHOLDER, "n_infeasible_paired": 0}
            continue
        result[m] = {
            "n_infeasible_paired": n,
            "objective_win_rate": f"{obj_win[m]}/{n}",
            "objective_tie_rate": f"{obj_tie[m]}/{n}",
            "objective_avg_diff": float(np.mean(obj_diffs[m])),
            "runtime_win_rate": f"{rt_win[m]}/{n}",
            "runtime_tie_rate": f"{rt_tie[m]}/{n}",
            "runtime_avg_diff": float(np.mean(rt_diffs[m])),
            "runtime_median_diff": float(np.median(rt_diffs[m])),
        }
    return result


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
                                      relax_freq, num_relaxed, objective,
                                      n_infeasible_paired,
                                      objective_win_rate, objective_tie_rate, objective_avg_diff,
                                      runtime_win_rate, runtime_tie_rate,
                                      runtime_avg_diff, runtime_median_diff}}}
        -- the objective_*/runtime_* fields are directional-vs-symmetric and
        feasopt-vs-symmetric pairwise comparisons (symmetric itself is "-"/
        nan, not compared against itself), restricted to queries that
        needed relaxation under BOTH sides (see _pairwise_vs_baseline).
        objective_win_rate/objective_tie_rate are "k/n" (higher objective
        wins); objective_avg_diff is mean(mode - symmetric). runtime_win_rate/
        runtime_tie_rate are "k/n" (lower clean_median_time_s wins);
        runtime_avg_diff/runtime_median_diff are mean/median(mode - symmetric),
        so negative means faster than symmetric.
      "runtime": {bound_pad: {mode: {n_infeasible_timed, median_s, mean_s}}}
      "infeasible": {bound_pad: {mode: {n, rouge1_f1, rouge2_f1, rougeL_f1,
                                         sbert, bound_shift, num_relaxed, objective}}}
        -- same quality metrics as "quality", but averaged only over the
        instances that actually required relaxation (relax_freq > 0).
      "raw": [ {bound_pad, mode, intent_idx, target, rouge1_f1, rouge2_f1,
                rougeL_f1, sbert, relax_freq, num_relaxed, bound_shift,
                objective, learn_time_s, ilp_time_s, clean_median_time_s}, ... ]
        -- one row per (bound_pad, mode, instance), pre-aggregation. This is
        exactly what "quality"/"infeasible"/"runtime" are averaged from.
      "n_instances", "bound_pads", "modes"
    """
    for m in modes:
        assert m in _MODEL_CLASSES, f"unknown mode {m}"

    random.seed(seed)
    udr = UserDataReader(users_path, data_path, 0, 275)
    instances = _build_instances(udr, num_examples, num_test, limit)
    scorer = EvaluationScore(shared_docs, data_path, n_topics)

    quality, runtime, infeasible = {}, {}, {}
    raw_rows = []

    for pad in bound_pads:
        models = {m: _MODEL_CLASSES[m](data_path, shared_docs, n_topics, num_examples,
                                        is_generative=False)
                  for m in modes}

        per_mode_records = {m: [] for m in modes}

        for inst in instances:
            # Same padded bounds handed to all 3 modes for this instance, so the
            # comparison is apples-to-apples (get_bounds is unchanged/inherited).
            base_bounds, _avg_len = models[modes[0]].get_bounds(inst["example_set"], bound_pad=pad)
            base_bounds = np.array(base_bounds, dtype=float)

            for m in modes:
                try:
                    with _capture_objective() as captured:
                        pred, learn_t, ilp_t, _slen, relax_freq, num_relaxed = \
                            models[m].get_predicted_summary(inst["target"], inst["example_set"],
                                                              bounds=base_bounds.copy())
                except Exception as e:
                    import traceback
                    print(f"[{m}] instance {inst['intent_idx']} failed: {e!r} filename={getattr(e, 'filename', None)}")
                    traceback.print_exc()
                    continue
                if pred.startswith("def_sum"):
                    continue

                rouge = scorer.compareScore(pred, inst["gt_text"])          # [[p,r,f1,f2] x3]
                sbert = scorer.compare_summaries_sbert(pred, inst["gt_text"])
                bound_shift = float(np.sum(np.abs(models[m].utilized_bounds - base_bounds)))
                objective = float(captured["value"]) if captured["value"] is not None else float("nan")

                clean_median_s = float("nan")
                if relax_freq > 0:
                    # Clean back-to-back timing (bench_runtime.py's method), median of `repeats`.
                    times = []
                    for _ in range(repeats):
                        t0 = time.perf_counter()
                        models[m].get_predicted_summary(inst["target"], inst["example_set"],
                                                          bounds=base_bounds.copy())
                        times.append(time.perf_counter() - t0)
                    clean_median_s = float(np.median(times))

                record = {
                    "rouge1_f1": rouge[0][2], "rouge2_f1": rouge[1][2], "rougeL_f1": rouge[2][2],
                    "sbert": sbert, "relax_freq": relax_freq, "num_relaxed": num_relaxed,
                    "bound_shift": bound_shift, "objective": objective,
                }
                per_mode_records[m].append(record)

                raw_rows.append({
                    "bound_pad": pad, "mode": m,
                    "intent_idx": inst["intent_idx"], "target": inst["target"],
                    **record,
                    "learn_time_s": learn_t, "ilp_time_s": ilp_t,
                    "clean_median_time_s": clean_median_s,
                })

        pairwise = _pairwise_vs_baseline(raw_rows, pad, modes)

        quality[pad], runtime[pad], infeasible[pad] = {}, {}, {}
        for m in modes:
            recs = per_mode_records[m]
            n = len(recs)
            quality[pad][m] = {
                "relax_rate": (sum(1 for r in recs if r["relax_freq"] > 0) / n) if n else float("nan"),
                "relax_freq": float(np.mean([r["relax_freq"] for r in recs])) if recs else float("nan"),
                **_mean_stats(recs),
                **pairwise[m],
            }
            infeasible[pad][m] = _mean_stats([r for r in recs if r["relax_freq"] > 0])
            medians = [r["clean_median_time_s"] for r in raw_rows
                       if r["bound_pad"] == pad and r["mode"] == m and r["relax_freq"] > 0]
            runtime[pad][m] = {
                "n_infeasible_timed": len(medians),
                "median_s": float(np.median(medians)) if medians else float("nan"),
                "mean_s":   float(np.mean(medians)) if medians else float("nan"),
            }

    return {
        "quality": quality, "runtime": runtime, "infeasible": infeasible, "raw": raw_rows,
        "n_instances": len(instances), "bound_pads": list(bound_pads), "modes": list(modes),
    }


_RAW_FIELDS = ("bound_pad", "mode", "intent_idx", "target", "rouge1_f1", "rouge2_f1",
               "rougeL_f1", "sbert", "relax_freq", "num_relaxed", "bound_shift", "objective",
               "learn_time_s", "ilp_time_s", "clean_median_time_s")

_SUMMARY_FIELDS = ("bound_pad", "mode", "n", "relax_rate", "relax_freq",
                    "rouge1_f1", "rouge2_f1", "rougeL_f1", "sbert",
                    "bound_shift", "num_relaxed", "objective",
                    "n_infeasible_timed", "median_clean_time_s", "mean_clean_time_s",
                    "n_infeasible_paired",
                    "objective_win_rate", "objective_tie_rate", "objective_avg_diff",
                    "runtime_win_rate", "runtime_tie_rate",
                    "runtime_avg_diff", "runtime_median_diff")


def write_raw_csv(report, path):
    """One row per (bound_pad, mode, instance) -- everything before averaging."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_RAW_FIELDS)
        w.writeheader()
        w.writerows(report["raw"])


def write_summary_csv(report, path):
    """One row per (bound_pad, mode): every metric discussed -- runtime,
    #constraints relaxed, total bound-relaxation amount, objective score,
    and ROUGE/SBERT -- averaged over ALL instances for that cell (the
    clean-timing columns remain infeasible-only, since that's the only
    subset they're ever measured on)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_SUMMARY_FIELDS)
        w.writeheader()
        for pad in report["bound_pads"]:
            for m in report["modes"]:
                q = report["quality"][pad][m]
                rt = report["runtime"][pad][m]
                w.writerow({
                    "bound_pad": pad, "mode": m, "n": q["n"],
                    "relax_rate": q["relax_rate"], "relax_freq": q["relax_freq"],
                    "rouge1_f1": q["rouge1_f1"], "rouge2_f1": q["rouge2_f1"],
                    "rougeL_f1": q["rougeL_f1"], "sbert": q["sbert"],
                    "bound_shift": q["bound_shift"], "num_relaxed": q["num_relaxed"],
                    "objective": q["objective"],
                    "n_infeasible_timed": rt["n_infeasible_timed"],
                    "median_clean_time_s": rt["median_s"], "mean_clean_time_s": rt["mean_s"],
                    "n_infeasible_paired": q["n_infeasible_paired"],
                    "objective_win_rate": q["objective_win_rate"],
                    "objective_tie_rate": q["objective_tie_rate"],
                    "objective_avg_diff": q["objective_avg_diff"],
                    "runtime_win_rate": q["runtime_win_rate"],
                    "runtime_tie_rate": q["runtime_tie_rate"],
                    "runtime_avg_diff": q["runtime_avg_diff"],
                    "runtime_median_diff": q["runtime_median_diff"],
                })


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
            ["n", "relax_rate", "rouge1_f1", "sbert", "bound_shift", "num_relaxed", "objective"])
    _print("Pairwise vs symmetric (paired-infeasible queries only)", report["quality"],
            ["n_infeasible_paired", "objective_win_rate", "objective_tie_rate", "objective_avg_diff",
             "runtime_win_rate", "runtime_tie_rate", "runtime_avg_diff", "runtime_median_diff"])
    _print("Quality, infeasible instances only (mean over relaxed instances)", report["infeasible"],
            ["n", "rouge1_f1", "rouge2_f1", "rougeL_f1", "sbert", "bound_shift", "num_relaxed", "objective"])
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
    ap.add_argument("--output_file", default="results/Item6/full_report/full_report",
                     help="Path prefix (directory + basename, no extension) for the two "
                          "output CSVs: <output_file>_raw.csv (per-instance rows, before "
                          "any averaging) and <output_file>_summary.csv (per-(bound_pad, "
                          "mode) averages: runtime, num_relaxed, bound_shift, objective, "
                          "rouge/sbert). Pass a different prefix per run to avoid "
                          "overwriting a previous run's output.")
    args = ap.parse_args()

    raw_out = f"{args.output_file}_raw.csv"
    summary_out = f"{args.output_file}_summary.csv"

    report = run_full_item6_report(
        args.data_path, args.shared_docs, args.users_path,
        bound_pads=args.bound_pads, modes=args.modes,
        num_examples=args.num_examples, num_test=args.num_test, n_topics=args.n_topics,
        limit=args.limit, repeats=args.repeats, seed=args.seed,
    )
    print_full_item6_report(report)

    write_raw_csv(report, raw_out)
    write_summary_csv(report, summary_out)
    print(f"Wrote raw per-instance rows to {raw_out}")
    print(f"Wrote per-(bound_pad, mode) averages to {summary_out}")


if __name__ == "__main__":
    main()
