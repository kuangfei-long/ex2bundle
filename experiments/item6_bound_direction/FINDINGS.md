# Revision Item 6 — Bound Direction: Findings

**Addresses:** Meta-1, R3.O2, R3.D2 · **Owner:** Kuangfei · **Dataset:** SubSume (RQ2 setting, 5 source / 3 target per intent) · **Run date:** 2026-07-02

Compares three bound-relaxation strategies:

- **symmetric** — current algorithm: IIS (ConflictRefiner) finds violated topics, then **both** bound sides are widened.
- **directional** — same IIS, but only the **violated side** moves.
- **feasopt** — CPLEX FeasOpt (`docplex.mp.relaxer.Relaxer`): one-shot **minimal** total relaxation.

All three evaluated on identical train/test splits. Reproduce with:

```
/Users/longzhuren/anaconda3/envs/InfoSecurity/bin/python experiments/item6_bound_direction/run_bound_direction.py \
  --data_path data/data_ctm.csv --shared_docs data/shared_docs/ \
  --users_path data/user_summary_jsons/ --results_path results/Item6/
```

Raw data: `item6_summary.csv`, `item6_records.pkl`.

## Table 1 — All 825 instances

| Mode | Runtime (s) | SBERT | ROUGE-1 | ROUGE-2 | ROUGE-L | Init width | Relaxed width | Bound shift | Relax freq | # relaxed |
|---|---|---|---|---|---|---|---|---|---|---|
| symmetric  | 0.442 | 0.8554 | 0.5399 | 0.3753 | 0.4118 | 1.4426 | 1.4439 | 0.0125 | 0.0145 | 0.0206 |
| directional| 0.444 | 0.8554 | 0.5399 | 0.3753 | 0.4118 | 1.4426 | 1.4433 | 0.0066 | 0.0145 | 0.0206 |
| feasopt    | 0.443 | 0.8553 | 0.5400 | 0.3753 | 0.4119 | 1.4426 | 1.4429 | 0.0025 | 0.0061 | 0.0133 |

## Table 2 — Relaxation-triggering subset (5 / 825 instances)

| Mode | Runtime (s) | SBERT | ROUGE-1 | ROUGE-L | Bound shift | Relax rounds | # relaxed |
|---|---|---|---|---|---|---|---|
| symmetric  | 1.39 | 0.7899 | 0.4748 | 0.3918 | 2.056 | 2.4 | 3.4 |
| directional| 1.44 | 0.7899 | 0.4748 | 0.3918 | 1.085 | 2.4 | 3.4 |
| feasopt    | 0.50 | 0.7667 | 0.4786 | 0.4007 | 0.411 | 1.0 | 2.2 |

## Conclusions

1. **Quality is invariant to relaxation direction.** ROUGE-1/2/L and SBERT are identical for symmetric vs directional (to 4 decimals) and near-identical for feasopt. Widening both sides vs one side vs minimal does not change output quality.
2. **Directional halves the bound shift at zero cost.** Bound shift drops 2.06 → 1.09 with identical quality, runtime, and iteration count (same IIS, 2.4 rounds / 3.4 topics). Answers R3.O2: the solver *can* pinpoint the violated side, and using that tightens the relaxation for free.
3. **FeasOpt is the tightest and fastest.** Smallest bound shift (0.411, ~5× tighter than symmetric) and ~2.8× faster on relaxing instances (0.50s vs 1.39s) because it is one-shot (1.0 round vs 2.4). Small SBERT cost (0.767 vs 0.790).
4. **Symmetric (current algo) is justified.** It "over-relaxes" the bounds but loses no quality, so its simplicity is defensible; directional is a free refinement if a tighter bound is desired.

## Bound-tightening stress-test (Tables 3–4)

Because only ~0.4% of SubSume instances relax under the paper-default padding
(`bound_pad=0.1`, ±10%), we tighten the synthesized bounds inward with a
negative `bound_pad` (`lb=min*(1-pad)`, `ub=max*(1+pad)`) to exercise the
relaxation algorithms on a real sample. The 5-source / 3-target protocol is
unchanged — only the intent bounds are tightened. 250-instance subset.

Reproduce:
```
run_bound_direction.py ... --bound_pads -0.3 -0.2 0.1 --limit 250
```
Outputs: `item6_summary.csv` (all), `item6_summary_relaxed_only.csv` (relaxed).

### Table 3 — relaxation rate vs tightening (all instances)

| bound_pad | relax_rate | (mode-independent; same IIS triggers) |
|---|---|---|
| 0.1 (default) | 0.4 % | 1 / 250 |
| -0.2 | 18.8 % | 47 / 250 |
| -0.3 | 60.0 % | 150 / 250 |

### Table 4 — relaxed-only comparison at each tightening level

**bound_pad = -0.2 (n = 47)**

| Mode | Runtime (s) | SBERT | ROUGE-1 | Bound shift | Relax rounds | # relaxed |
|---|---|---|---|---|---|---|
| symmetric  | 4.92 | 0.8242 | 0.5019 | 1.096 | 1.83 | 1.64 |
| directional| 5.32 | 0.8242 | 0.5019 | 0.856 | 1.83 | 1.64 |
| feasopt    | 3.21 | 0.8207 | 0.4880 | 0.209 | 1.00 | 1.83 |

**bound_pad = -0.3 (n = 150)**

| Mode | Runtime (s) | SBERT | ROUGE-1 | Bound shift | Relax rounds | # relaxed |
|---|---|---|---|---|---|---|
| symmetric  | 5.70 | 0.8498 | 0.5111 | 1.332 | 2.79 | 1.40 |
| directional| 5.81 | 0.8494 | 0.5085 | 1.205 | 2.79 | 1.40 |
| feasopt    | 7.23 | 0.8373 | 0.4986 | 0.394 | 1.00 | 2.51 |

### Findings from the sweep

1. **Bound-shift ordering symmetric > directional > feasopt holds at every tightening level**; FeasOpt is ~5× tighter than symmetric.
2. **Directional's advantage shrinks as bounds tighten** (~22% smaller shift at -0.2, ~10% at -0.3): under severe infeasibility both sides get violated, so directional ≈ symmetric.
3. **Quality is essentially invariant** (symmetric ≈ directional to 3 decimals; FeasOpt slightly lower — a small quality cost for much tighter bounds).
4. **FeasOpt is a "surgical" strategy**: one shot (1.0 round) spreading minimal relaxation over *more* topics (2.51 vs 1.40) instead of large shifts on few. Its runtime is non-monotonic — faster than symmetric under mild tightening (-0.2), slower under severe (-0.3), as the one-shot FeasOpt solve gets costlier on harder infeasibility.

## Severity sweep — quality vs #relaxation-rounds (Table 5, Fig 2)

Reviewer follow-up: (a) restrict to instances that are infeasible from the
start, and (b) push severity well past 10 relaxation rounds — does output
quality stay identical across strategies as severity grows?

Setup: aggressive tightening `bound_pad ∈ {-0.3,-0.4,-0.5,-0.6}`, 100-instance
subset (`results/Item6/severity/`). Pool the **341 infeasible-from-start**
instances and bin by the number of relaxation rounds the iterative methods
need (symmetric's relax_freq). Reproduce:
```
run_bound_direction.py ... --bound_pads -0.3 -0.4 -0.5 -0.6 --limit 100
python experiments/item6_bound_direction/plot_severity.py    # -> fig_item6_severity.png
```

| Rounds | n | ROUGE-1 sym/dir/feas | SBERT sym/dir/feas | bound_shift sym/dir/feas |
|---|---|---|---|---|
| 1-2   | 59 | 0.520/0.520/0.527 | 0.848/0.849/0.856 | 1.00/0.85/0.19 |
| 3-4   | 63 | 0.475/0.475/0.481 | 0.820/0.820/0.819 | 1.81/1.63/0.60 |
| 5-6   | 54 | 0.492/0.495/0.487 | 0.827/0.827/0.820 | 2.67/2.50/1.04 |
| 7-9   | 50 | 0.490/0.490/0.484 | 0.828/0.830/0.822 | 3.67/3.39/1.49 |
| 10-14 | 72 | 0.490/0.490/0.501 | 0.832/0.832/0.837 | 5.40/5.00/2.72 |
| 15+   | 43 | 0.565/0.564/0.598 | 0.874/0.873/0.868 | 8.23/7.76/4.97 |

**Findings:**
1. **No strategy is systematically better on quality at any severity — but this is MEAN parity, not per-output parity.** Group-mean ROUGE/SBERT agree to within ~0.01–0.03 at every severity. However, a *paired per-instance* check (below) shows FeasOpt's individual outputs do differ from the iterative ones; the differences just cancel on average. Symmetric vs Directional, by contrast, are identical per-instance.

**Paired per-instance quality (341 infeasible instances):**

| Pair | metric | mean \|Δ\| | % instances \|Δ\|>0.05 | signed Δ |
|---|---|---|---|---|
| sym vs dir | ROUGE-1 | 0.003 | 2% | +0.0003 |
| sym vs dir | SBERT | 0.001 | 1% | +0.0002 |
| sym vs feasopt | ROUGE-1 | 0.058 | 47% | +0.007 |
| sym vs feasopt | ROUGE-2 | 0.081 | 50% | +0.009 |
| sym vs feasopt | ROUGE-L | 0.074 | 50% | +0.007 |
| sym vs feasopt | SBERT | 0.036 | 25% | −0.0004 |

So "identical quality across all three" is only true in the mean and only literally true for symmetric vs directional. FeasOpt selects different sentences, so ~half its per-instance ROUGE scores differ by >0.05 from the iterative methods — but with near-zero signed mean, i.e. no systematic winner. (Note the mild tension: FeasOpt's own merit objective is ~8% lower yet its ROUGE is marginally, borderline-significantly higher — merit ≠ ROUGE.)

**Paired significance + equivalence tests (n=341 infeasible instances):**

| Pair | metric | mean Δ | Cohen's dz | paired-t p | Wilcoxon p | TOST ±0.02 |
|---|---|---|---|---|---|---|
| sym vs dir | ROUGE-1 | +0.0003 | 0.02 | 0.72 | 0.85 | EQUIV (≈0) |
| sym vs dir | SBERT | +0.0002 | 0.03 | 0.59 | 0.96 | EQUIV (≈0) |
| sym vs feasopt | ROUGE-1 | +0.0072 | 0.09 | 0.11 | 0.059 | EQUIV (0.002) |
| sym vs feasopt | ROUGE-2 | +0.0085 | 0.07 | 0.19 | 0.051 | EQUIV (0.038) |
| sym vs feasopt | ROUGE-L | +0.0072 | 0.07 | 0.22 | 0.083 | EQUIV (0.014) |
| sym vs feasopt | SBERT | −0.0004 | 0.01 | 0.89 | 0.55 | EQUIV (≈0) |

**Conclusion (statistically grounded):** no pair/metric reaches a significant
difference (paired-t p>0.10 everywhere); effect sizes are negligible (|dz|≤0.09);
and TOST equivalence tests pass for every pair/metric at a ±0.02 margin — a
*positive* conclusion of statistical equivalence, not merely failure to detect.
Caveats: (i) sym≈dir equivalence is extremely tight (TOST p≈0); FeasOpt-vs-iterative
equivalence holds but the Wilcoxon p's sit at ~0.05–0.06 for ROUGE — a weak,
non-significant hint that FeasOpt's ROUGE is slightly higher (SBERT shows nothing).
(ii) The ±0.02 equivalence margin is a chosen "negligible" threshold; state it explicitly.
2. **Bound-shift ordering symmetric > directional > feasopt holds and the gap widens with severity** (at 15+ rounds FeasOpt is ~40% tighter than symmetric). Directional's advantage over symmetric shrinks as severity grows (7.76 vs 8.23 at 15+).
3. **Runtime** (see clean benchmark below): symmetric ≈ directional at all severities; FeasOpt runtime is ~flat while the iterative methods grow with severity.

## Clean runtime benchmark (Table 6)

The sweep's runtime numbers were unreliable (killed/resumed across processes
under variable laptop load). `bench_runtime.py` re-measures runtime
fairly: single process, three strategies back-to-back on the same instance,
NO ROUGE/SBERT scoring, median of 3 repeats. pad=-0.5, 80 infeasible instances,
binned by relaxation rounds. Model time only (`get_predicted_summary`).

| Rounds | n | Symmetric (s) | Directional (s) | FeasOpt (s) | FeasOpt/Sym |
|---|---|---|---|---|---|
| 1-2   | 8  | 1.41 | 1.48 | 1.45 | 1.03× |
| 3-4   | 9  | 2.16 | 1.98 | 1.27 | 0.59× |
| 5-6   | 21 | 1.38 | 1.34 | 1.52 | 1.10× |
| 7-9   | 18 | 1.86 | 1.88 | 1.53 | 0.82× |
| 10-14 | 22 | 8.59 | 8.64 | 1.84 | 0.21× |
| 15+   | 2  | 5.83 | 5.39 | 1.33 | 0.23× |

**Findings:**
1. **Symmetric ≈ Directional at every severity** — they track within noise (same IIS, same round count; only the widen-both-vs-one-side step differs).
2. **FeasOpt runtime is ~flat (~1.3–1.8 s); the iterative methods blow up with severity** — at 10–14 rounds symmetric/directional take ~8.6 s vs FeasOpt's ~1.8 s (**~5× faster**). This is structural: FeasOpt solves once, whereas each iterative round costs one ILP solve *plus* one (expensive) ConflictRefiner call, so cost grows with the round count. Below ~6 rounds the three are comparable.
3. Corrects the earlier record: the first "FeasOpt slower under severe infeasibility" claim was process-split noise; the clean, load-independent scaling law is the opposite — **FeasOpt scales better and wins runtime under severe infeasibility**, ties at low severity.

Caveat: absolute seconds are laptop + Community-CPLEX + ~100-var pool specific, but the *relative* scaling (iterative grows with rounds, FeasOpt flat) is algorithmic and hardware-robust.

## Solution & objective comparison (Table 7) — do the strategies really agree?

Reviewer (Matteo): identical ROUGE/SBERT is surprising — are the *solutions*
(selected sentences) and the *objective/merit* actually the same, or just the
score? `bench_solutions.py` runs all three on the same query and records
the selected sentence ids, the final ILP objective, and bound shift. 177
infeasible-from-start queries (pads -0.2/-0.3/-0.5).

| Pair | Bundles identical | Mean Jaccard | Mean obj rel-diff | Mean bound-shift diff |
|---|---|---|---|---|
| symmetric vs directional | 96.6% | 0.988 | 0.08% | 0.195 |
| symmetric vs feasopt      | 6.2%  | 0.420 | 8.15% | 1.535 |
| directional vs feasopt    | 6.2%  | 0.418 | 8.07% | 1.340 |

Signed objective (41 infeasible, pad -0.3): `feasopt_obj − symmetric_obj`
mean −1.02, median −0.69; FeasOpt objective is **lower in 85%** of cases.

**Findings:**
1. **Symmetric ≈ Directional in every respect** — same bundle 96.6% of the time (Jaccard 0.99), objective within 0.08%. Relaxation *direction* (both-sides vs one-side) does not change the output; directional only yields marginally tighter recorded bounds. Clean answer to R3.O2.
2. **FeasOpt produces genuinely different solutions** — only 6% identical bundles, ~42% sentence overlap — with a **lower** merit objective (~8% lower, because minimal relaxation → smaller feasible region), and the largest bound difference.
3. **So we are NOT in the "bounds differ but objective identical" situation** Matteo hypothesized — FeasOpt's solution *and* objective both differ. Yet (from the severity experiment) ROUGE/SBERT quality is identical across all three. Interpretation: the task has a plateau of near-equivalent good bundles; the relaxation strategy changes *which* bundle and its merit, but not the downstream quality.
4. **Supports keeping simple symmetric relaxation:** quality is robust to the strategy; symmetric is solver-agnostic (FeasOpt is CPLEX-specific; HiGHS has no exact equivalent) and, by relaxing more, keeps a *higher* merit objective than FeasOpt without any quality loss.

**Symmetric vs Directional merit (165 infeasible queries):** symmetric's objective
is **≥ directional's in 100% of cases — never lower** (equal 96.4%, strictly higher
3.6%; mean Δ +0.016, min 0). Theory: symmetric widens both sides of each violated
topic, so its feasible region is a *superset* of directional's, and maximizing merit
over a superset can only weakly increase it. → symmetric weakly dominates directional:
statistically-equivalent quality, never-worse merit, occasionally better.

**Why FeasOpt is not preferable (Matteo):** FeasOpt minimizes total slack, it does not
maximize merit — it converges to the least-perturbation feasible bundle and can miss a
higher-merit one (hence the ~8% lower merit). Our formulation maximizes the merit
objective under the relaxed bounds, so swapping in a better merit function improves the
relaxation for free. (Whether the merit score itself tracks true user preference is an
orthogonal question, studied in Appendix B.)

## Caveat / next steps

- The paper-default (`bound_pad=0.1`) relaxes almost never on SubSume; the tightening sweep above is what makes the comparison statistically meaningful. Frame it as a controlled stress-test.
- Figure: `fig_item6_bound_shift.png` (bound shift + relax rate vs tightening).
- CNN/DailyMail half of Item 6 is **not implemented** (needs a topic-scored CSV + SBERT embeddings for CNN/DM — a separate pipeline; SubSume-first by choice).
