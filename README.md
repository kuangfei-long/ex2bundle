# Ex2Bundle

> **Example-Driven Intent Synthesis for Constrained Data Bundle Retrieval:
> Focused Text Snippet Extraction and Beyond**
>
> Whanhee Cho¹, Kuangfei Long², Mahmood Jasim³, Matteo Brucato⁴,
> Alexandra Meliou⁵, Peter J. Haas⁵, Anna Fariha¹
>
> ¹University of Utah · ²Boston University · ³Louisiana State University ·
> ⁴OSM Data · ⁵UMass Amherst
>
> Submitted to **VLDB 2027**
>
> 📄 **Technical Report**: [Link](https://afariha.github.io/papers/ex2bundle_tech_rep.pdf)

This repository is the official artifact for the paper. Its purpose is the
**reproducibility** of every experiment presented in the paper: bound
synthesis, bound relaxation, the slider interface, the quality function, the
package-query execution, all baselines (Top-k SBERT, SuDocu, MemSum,
BertSumExt), and the deployed Flask demo used in the user study.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Repository layout

```
ex2bundle/
├── README.md
├── requirements.txt
├── models/                              # Core algorithm + baselines (Section 4–5)
│   ├── base.py                          # 4.1.1 Bound synthesis (SuDocuBase)
│   ├── ex2bundle.py                     # 4.1.2 + 4.3 Main Ex2Bundle model
│   ├── ex2bundle_slider.py              # 4.1.3 Slider relaxation (used by demo)
│   ├── sbert_baseline.py                # 5.1.3 Top-k SBERT baseline
│   ├── sudocu_baseline.py               # 5.1.3 SuDocu baseline (LDA + simple relax)
│   └── memsum_bertsum_collector.py      # 5.1.3 SBERT pre-filter for MemSum / BertSumExt
├── utils/
│   ├── data_reader.py
│   ├── evaluation.py                    # ROUGE + SBERT metrics
│   ├── filtering.py                     # SBERT candidate pre-filter
│   ├── quality.py                       # 4.2 Quality variants (C-FREQ / BS / P-FREQ / TS / ALL)
│   └── slider.py                        # 4.1.3 Slider math
├── experiments/
│   ├── runner.py                        # SubSumE experiment loop
│   ├── synthetic_runner.py              # Synthetic-data experiment loop
│   ├── generate_synthetic_data.py       # 5.7 Three sampling strategies
│   ├── run_figure9_subsume.py           # 5.3 RQ2 Figure 9 (all baselines)
│   ├── run_figure12_variants.py         # 5.5 Figure 12 quality ablation
│   ├── run_figure13_relaxation.py       # 5.6 RQ3 Figure 13
│   ├── run_figure14_scalability.py      # 5.7 RQ4 Figure 14 (3-curve × 3-panel)
│   ├── run_table8_tpch.py               # 5.2 RQ1 Table 8 TPC-H
│   ├── collect_memsum_bertsum_data.py   # 5.3 Generate input for MemSum/BertSumExt
│   └── cnn_dailymail/                   # 5.1.2 CNN/DailyMail pipeline
│       ├── preprocess.py                #   Article → sentence-level JSON
│       ├── gpt4o_sentence_matcher.py    #   GPT-4o highlight → article sentences
│       └── README.md
├── data/
│   ├── README.md                        # Data setup instructions
│   ├── data_ctm.csv                     # SubSumE topic-scored sentences
│   ├── user_summary_jsons/              # SubSumE user summaries (275 files)
│   ├── shared_docs/                     # state_indices.txt, stopwords.txt, StateDocuments/
│   └── cnn_dailymail/                   # 200 pre-processed CNN/DM articles
├── demo/                                # Section 6 — User study Flask app
│   ├── README.md
│   ├── server_code/                     # Flask backend + slider model
│   └── demo_site/                       # Older standalone demo
├── docs/
│   └── chatgpt_prompts.md               # Tables 10/11 GPT-4o prompts (manual)
└── notebooks/
    └── results_analysis.ipynb           # Load .npz / .pkl and plot
```

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

CPLEX (via `docplex` + `cplex` Python packages) is required for the ILP.

### 2. Set up data

See `data/README.md` for SubSumE / TPC-H / CNN-DM data setup. The SubSumE
data, CNN/DailyMail pre-processed articles, and shared docs are all already
in this repo (post-migration). Only the TPC-H DB needs to be built locally.

---

## Running each paper experiment

### RQ1 — Table 8 (TPC-H constraint satisfaction)

```bash
python experiments/run_table8_tpch.py --db_path data/tpch.db --runs 5
```

### RQ2 — Figure 9 (SubSumE retrieval comparison)

Run all three local baselines:
```bash
python experiments/run_figure9_subsume.py \
    --data_path   data/data_ctm.csv \
    --users_path  data/user_summary_jsons/ \
    --shared_docs data/shared_docs/ \
    --models      ex2bundle topk_sbert sudocu \
    --num_trials  2 --no_mp
```

For MemSum / BertSumExt:
```bash
# Step 1: pre-filter and dump input files for the external models
python experiments/collect_memsum_bertsum_data.py \
    --data_path   data/data_ctm.csv \
    --users_path  data/user_summary_jsons/ \
    --shared_docs data/shared_docs/ \
    --num_trials  2

# Step 2: run BertSumExt / MemSum on the produced .story / .json files,
# then evaluate their summaries with utils/evaluation.py.
```

ChatGPT-4o results (Tables 10/11) were obtained by manually pasting prompts
from `docs/chatgpt_prompts.md` into the GPT-4o web interface — no automated
runner is included.

### Figure 12 — Quality-function ablation

```bash
for OBJ in C-FREQ BS P-FREQ TS ALL; do
  python experiments/run_figure12_variants.py \
      --objective $OBJ \
      --data_path   data/data_ctm.csv \
      --users_path  data/user_summary_jsons/ \
      --shared_docs data/shared_docs/ \
      --no_mp
done
```

### RQ3 — Figure 13 (relaxation frequency)

```bash
# Step 1: generate synthetic data (single-feature only — fastest)
python experiments/generate_synthetic_data.py \
    --data_csv    data/data_ctm.csv \
    --states_file data/shared_docs/just_states.txt \
    --output_dir  data/synthetic_data_collection/ \
    --strategy    single

# Step 2: run experiment + plot
python experiments/run_figure13_relaxation.py \
    --data_path       data/data_ctm.csv \
    --shared_docs     data/shared_docs/ \
    --synthetic_data  data/synthetic_data_collection/single/ \
    --states_file     data/shared_docs/just_states.txt \
    --results_path    results/Figure13/
```

### RQ4 — Figure 14 (scalability, 3 curves × 3 panels)

```bash
# Step 1: generate ALL three sampling strategies
python experiments/generate_synthetic_data.py \
    --data_csv    data/data_ctm.csv \
    --states_file data/shared_docs/just_states.txt \
    --output_dir  data/synthetic_data_collection/ \
    --strategy    all

# Step 2: run experiment over each strategy + combined plot
python experiments/run_figure14_scalability.py \
    --data_path       data/data_ctm.csv \
    --shared_docs     data/shared_docs/ \
    --synthetic_root  data/synthetic_data_collection/ \
    --states_file     data/shared_docs/just_states.txt \
    --results_path    results/Figure14/
```

### Section 6 — User study demo

See `demo/README.md`. Run with `python -m flask_code.app` from
`demo/server_code/`.

---

## Paper ↔ code map

| Paper section | File(s) |
|---|---|
| 4.1.1 Bound synthesis | `models/base.py:get_bounds` |
| 4.1.2 ConflictRefiner relaxation | `models/ex2bundle.py:_identify_violated_constraints` |
| 4.1.2 Range heuristic (fallback) | `models/ex2bundle.py:_identify_violated_constraints` |
| 4.1.2 Step size ε_j (δ=0.5) | `models/ex2bundle.py:get_predicted_summary` |
| 4.1.3 Slider (α=0.1, β=98) | `utils/slider.py`, `models/ex2bundle_slider.py` |
| 4.1.4 Algorithm 1 | `models/ex2bundle.py:get_predicted_summary` |
| 4.2 Quality function | `utils/quality.py:Objective_Function_Wrapper` |
| 4.3 PaQL / ILP | `models/ex2bundle.py` (CPLEX ILP) |
| 5.1.2 Datasets | `data/`, `experiments/cnn_dailymail/` |
| 5.1.3 Top-k baseline | `models/sbert_baseline.py` |
| 5.1.3 SuDocu baseline | `models/sudocu_baseline.py` |
| 5.1.3 MemSum / BertSumExt | `models/memsum_bertsum_collector.py` + `experiments/collect_memsum_bertsum_data.py` |
| 5.1.3 ChatGPT-4o | `docs/chatgpt_prompts.md` (manual queries) |
| 5.2 RQ1 Table 8 | `experiments/run_table8_tpch.py` |
| 5.3 RQ2 Figure 9 | `experiments/run_figure9_subsume.py` |
| 5.4 Tables 10 / 11 | `docs/chatgpt_prompts.md` |
| 5.5 Figure 12 | `experiments/run_figure12_variants.py` |
| 5.6 RQ3 Figure 13 | `experiments/run_figure13_relaxation.py` |
| 5.7 RQ4 Figure 14 | `experiments/run_figure14_scalability.py` + 3 strategies in `generate_synthetic_data.py` |
| 6 User study | `demo/` |

**ChatGPT-4o automation deliberately omitted.** Tables 10/11 were generated
by manually pasting prompts into the GPT-4o web interface — the prompts
themselves are in `docs/chatgpt_prompts.md` for reproducibility, but no API
runner is included.

---

## Citation

If you use this software or build on the algorithm, please cite the paper.
See [CITATION.cff](CITATION.cff) for the full author list and citation entry.
