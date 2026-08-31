# SketchRefine Scalability

Supplementary experiment for **Paper Section 4.5**: comparing the DIRECT
retrieval method (Section 4.3 — one CPLEX ILP over the whole candidate pool)
against SKETCH-REFINE (Section 4.5 — partition the pool, solve a small
sketch, then greedily refine it back to real tuples) on the SubSumE dataset.

The two methods live in [`models/ex2bundle.py`](../../models/ex2bundle.py)'s
`get_predicted_summary`, selected via the `do_sketch_refine` flag:

| method | how it retrieves the bundle |
|---|---|
| `direct` (`do_sketch_refine=False`, default) | one CPLEX ILP over the whole SBERT-prefiltered candidate pool |
| `sketch_refine` (`do_sketch_refine=True`) | [`utils/sketch_refine.py`](../../utils/sketch_refine.py)'s `SketchRefineSolver`: PARTITION the pool into groups, SKETCH over group representatives, then REFINE back to real tuples |

Both methods run on the *identical* instance (same model, same bounds, same
candidate pool), so the comparison isolates the retrieval algorithm itself.
Instances are binned into terciles of `avg_len` (the target package length,
which sets the candidate-pool size — `pool_size = avg_len * 10`, see
`models/ex2bundle.py:get_predicted_summary`) so the runtime curves show how
each method scales as the problem grows.

> **Environment:** run everything with the `InfoSecurity` conda env
> (`/Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python`) — it has
> docplex + cplex + sentence-transformers. Note CPLEX here is the Community
> edition (≤1000 vars), which bounds how large a candidate pool DIRECT can
> even attempt — part of SKETCH-REFINE's motivation.

## Scripts

| script | purpose | key outputs |
|---|---|---|
| `run_sketchrefine_scalability.py` | Runs both methods over identical SubSumE instances, computes runtime (wall/learn/ILP), quality (ROUGE/SBERT), summary length, and relaxation counts, binned by candidate-pool size. | `sketchrefine_records.pkl`, `sketchrefine_summary.csv`, `fig_sketchrefine_runtime.png` |

## Reproduce

```bash
PY=/Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python
DATA="--data_path data/data_ctm.csv --shared_docs data/shared_docs/ --users_path data/user_summary_jsons/"

$PY experiments/sketchrefine_scalability/run_sketchrefine_scalability.py $DATA \
    --results_path results/SketchRefine
```

Useful flags:

- `--limit N` — cap the number of instances (quick smoke run).
- `--sketch_refine_size_threshold`, `--sketch_refine_radius_limit`,
  `--max_repeat_cap`, `--sketch_refine_timelimit` — forwarded to
  `Ex2Bundle`'s SKETCH-REFINE knobs (see `models/ex2bundle.py`'s constructor
  and `utils/sketch_refine.py:SketchRefineSolver`'s docstring).

## Summary-CSV columns

| column | meaning |
|---|---|
| `size_bin` | `small` / `medium` / `large` tercile of `avg_len` across the run's instances |
| `method` | `direct` or `sketch_refine` |
| `n` | number of instances in the cell |
| `avg_len` | mean target package length (drives candidate-pool size) |
| `runtime_s`, `learn_s`, `ilp_s` | mean wall-clock / bound-synthesis+build / solve time per instance |
| `summary_len` | mean number of sentences in the returned bundle |
| `sbert`, `rouge1`, `rouge2`, `rougeL` | summary-quality metrics against the user's reference summary |
| `relax_freq` | mean number of bound-relaxation rounds |
