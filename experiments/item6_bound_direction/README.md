# Item 6 — Bound-Direction Relaxation

Supplementary experiments for **Revision Item 6** (addresses R3.O2 / R3.D2):
comparing three strategies for relaxing an infeasible package-query's topic
bounds, on the SubSume dataset.

The three strategies live in [`models/ex2bundle.py`](../../models/ex2bundle.py)
behind the `relaxation_mode` constructor flag:

| mode | how it relaxes an infeasible ILP |
|---|---|
| `symmetric` | **current algorithm** — CPLEX ConflictRefiner (IIS) finds the violated topics, then **both** sides of each are widened, iterating until feasible |
| `directional` | same IIS, but only the **violated side** is widened |
| `feasopt` | one-shot CPLEX FeasOpt (`docplex.mp.relaxer.Relaxer`) — the **minimal total** bound relaxation |

The bound-tightening knob `bound_pad` (in
[`models/base.py`](../../models/base.py) `get_bounds`) controls padding around
the example min/max: `0.1` = paper default (±10%); a **negative** value
tightens the bounds inward to *induce* infeasibility and stress-test the
relaxation algorithms.

> **Environment:** run everything with the `InfoSecurity` conda env
> (`/Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python`) — it has
> docplex + cplex + sentence-transformers. Note CPLEX here is the Community
> edition (≤1000 vars), which is fine for Item 6's small candidate pools.

## Scripts

| script | purpose | key outputs |
|---|---|---|
| `run_bound_direction.py` | Main driver. Runs the 3 modes over identical SubSume splits, optionally sweeping `--bound_pads`. Computes ROUGE/SBERT, runtime, bounds, relaxation counts. Checkpoints per `(pad, mode)` cell (resume-safe). | `item6_records.pkl`, `item6_summary.csv`, `item6_summary_relaxed_only.csv` |
| `bench_runtime.py` | **Clean** runtime comparison: single process, 3 modes back-to-back per query, no scoring, median of repeats. Binned by relaxation rounds. | `runtime_bench.csv` |
| `bench_solutions.py` | Do the strategies produce the same *solution*? Compares selected-sentence overlap (Jaccard), final objective/merit, bound shift, and signed merit dominance. | `solution_diffs.csv` |
| `analyze_severity.py` | Reads the record pkls (no re-run): natural infeasibility base rate, round distribution, and per-instance metrics binned by severity. | stdout tables |
| `analyze_significance.py` | Paired t-test, Wilcoxon, and TOST **equivalence** tests on per-instance ROUGE/SBERT. | stdout tables |
| `plot_bound_shift.py` | Fig: relaxation rate + bound shift vs bound tightening. | `sweep/fig_item6_bound_shift.png` |
| `plot_severity.py` | Fig: bound shift / ROUGE-1 / SBERT vs relaxation rounds. | `severity/fig_item6_severity.png` |

## Runs & result layout

The narrative write-up is [`FINDINGS.md`](FINDINGS.md) in this directory
(tracked). The raw run artifacts (pkl/CSV/PNG) are regenerable and live under
`results/Item6/`, which is git-ignored:

```
results/Item6/           (git-ignored — regenerate with the commands below)
├── baseline/            <- 825 queries at the default pad=0.1 (natural infeasibility rate)
├── sweep/               <- 250 queries × pads {0.1,-0.2,-0.3} (relaxation-rate curve)
└── severity/            <- 100 queries × aggressive pads {-0.3..-0.6}; plus runtime & solution benches
```

### Reproduce

```bash
PY=/Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python
DATA="--data_path data/data_ctm.csv --shared_docs data/shared_docs/ --users_path data/user_summary_jsons/"

# 1. Baseline (natural infeasibility rate at default bounds)
$PY experiments/item6_bound_direction/run_bound_direction.py $DATA \
    --bound_pads 0.1 --results_path results/Item6/baseline

# 2. Tightening sweep (relaxation-rate curve)
$PY experiments/item6_bound_direction/run_bound_direction.py $DATA \
    --bound_pads 0.1 -0.2 -0.3 --limit 250 --results_path results/Item6/sweep

# 3. Severity sweep (push to 10+ relaxation rounds)
$PY experiments/item6_bound_direction/run_bound_direction.py $DATA \
    --bound_pads -0.3 -0.4 -0.5 -0.6 --limit 100 --results_path results/Item6/severity

# 4. Clean runtime + solution/objective benches
$PY experiments/item6_bound_direction/bench_runtime.py   $DATA --bound_pad -0.5 --limit 80 --repeats 3
$PY experiments/item6_bound_direction/bench_solutions.py $DATA --bound_pads -0.2 -0.3 -0.5 --limit 100

# 5. Analyses + figures (read the pkls, no re-run)
$PY experiments/item6_bound_direction/analyze_severity.py
$PY experiments/item6_bound_direction/analyze_significance.py
$PY experiments/item6_bound_direction/plot_bound_shift.py
$PY experiments/item6_bound_direction/plot_severity.py
```

## Headline findings (see [`FINDINGS.md`](FINDINGS.md) for the full write-up)

- **Quality:** statistically **equivalent** across all three strategies at every
  severity (TOST passes at ±0.02; paired tests n.s.). No systematic winner.
- **Solutions:** symmetric ≈ directional (96.6% identical bundles); FeasOpt picks
  genuinely different sentences (≈6% identical) with **~8% lower merit** — it
  minimizes slack, not merit.
- **Merit dominance:** symmetric ≥ directional in **100%** of infeasible queries
  (its feasible region is a superset).
- **Bound shift:** symmetric > directional > FeasOpt (FeasOpt ~5× tighter), gap
  widens with severity.
- **Runtime:** symmetric ≈ directional; FeasOpt flat while the iterative methods
  grow (~5× slower at 10+ rounds).
- **Severity is rare in practice:** only 0.6% of queries are infeasible at the
  default bounds; when induced, ~81% resolve in ≤2 rounds.
- **Portability:** FeasOpt is CPLEX-specific; the iterative symmetric method is
  solver-agnostic (ports to e.g. HiGHS unchanged).

**Not yet done:** the CNN/DailyMail half of Item 6 (needs a topic-scored CSV +
SBERT embeddings for CNN/DM — a separate pipeline).
