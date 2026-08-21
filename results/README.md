# Results

Result tables and figures for the paper and its revision items. These are
**tracked on purpose**: every number quoted in a write-up should be checkable
here without re-running an experiment (some runs take hours and need CPLEX).

Each experiment driver writes here via `--results_path`; the layout below is
what the committed runs used.

```
results/
└── Item6/        Revision Item 6 — bound-direction relaxation (R3.O2 / R3.D2)
    ├── baseline/   825 queries at the paper default pad = 0.1
    ├── sweep/      250 queries × bound_pad {0.1, -0.2, -0.3}
    └── severity/   100 queries × bound_pad {-0.3 … -0.6}, plus the runtime
                    and solution/objective benches
```

Write-up: [`experiments/item6_bound_direction/FINDINGS.md`](../experiments/item6_bound_direction/FINDINGS.md).
Scripts and reproduce commands: [`experiments/item6_bound_direction/README.md`](../experiments/item6_bound_direction/README.md).

## Files

| file | produced by | contents |
|---|---|---|
| `item6_summary.csv` | `run_bound_direction.py` | one row per (`bound_pad`, `relaxation_mode`): aggregated quality, runtime, bound, and relaxation metrics over all queries |
| `item6_summary_relaxed_only.csv` | `run_bound_direction.py` | same aggregation restricted to the queries that actually triggered a relaxation (the only rows where the strategies can differ) |
| `item6_records.pkl` | `run_bound_direction.py` | raw per-query records (plain dicts/lists) — the input consumed by `analyze_severity.py`, `analyze_significance.py`, and both plot scripts |
| `runtime_bench.csv` | `bench_runtime.py` | clean single-process runtime per strategy, binned by number of relaxation rounds |
| `solution_diffs.csv` | `bench_solutions.py` | bundle overlap (Jaccard), final merit objective, and signed merit dominance between strategies, with the sample size each percentage is computed over |
| `fig_item6_bound_shift.png` | `plot_bound_shift.py` | relaxation rate and bound shift vs bound tightening |
| `fig_item6_severity.png` | `plot_severity.py` | bound shift, ROUGE-1, and SBERT vs relaxation rounds |

## Summary-CSV columns

| column | meaning |
|---|---|
| `bound_pad` | padding around the example min/max bounds. `0.1` = paper default (±10%); negative values tighten inward to induce infeasibility |
| `mode` | relaxation strategy: `symmetric` (current algorithm), `directional`, `feasopt` |
| `n` | number of queries in the cell |
| `relax_rate` | fraction of queries whose ILP was infeasible and had to be relaxed |
| `runtime_s` | mean wall-clock per query. Measured on a laptop under Community CPLEX — treat as indicative; `runtime_bench.csv` is the clean measurement |
| `sbert`, `rouge1`, `rouge2`, `rougeL` | summary-quality metrics against the user's reference summary |
| `init_width`, `relaxed_width` | mean total bound width before / after relaxation |
| `bound_shift` | total absolute movement of the bounds, `Σ|relaxed − initial|` — the main quantity distinguishing the three strategies |
| `relax_freq` | mean number of relaxation rounds (FeasOpt is one-shot, so ≤ 1) |
| `num_relaxed` | mean number of distinct topics whose bounds were relaxed |
