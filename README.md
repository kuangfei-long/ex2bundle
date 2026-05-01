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
> 📄 **Technical Report**: [Link](http://users.cs.utah.edu/~afariha/ex2bundle_tech_rep.pdf)

This repository is the official artifact for the paper. Its purpose is the
**reproducibility** of every experiment presented in the paper: bound
synthesis, bound relaxation, the slider interface, the quality function, the
package-query execution, all baselines (Top-k SBERT, SuDocu, PreSumm,
MemSum), and the deployed Flask demo used in the user study.

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
│   ├── sbert_baseline.py                # 5.1 Top-k SBERT baseline
│   ├── sudocu_baseline.py               # 5.1 SuDocu baseline (LDA + simple relax)
│   └── memsum_bertsum_collector.py      # 5.1 SBERT pre-filter for PreSumm / MemSum
├── utils/
│   ├── data_reader.py
│   ├── evaluation.py                    # ROUGE + SBERT metrics
│   ├── filtering.py                     # SBERT candidate pre-filter
│   ├── quality.py                       # 4.2 Quality variants (C-FREQ / BS / P-FREQ / TS / ALL)
│   └── slider.py                        # 4.1.3 Slider math
├── experiments/
│   ├── runner.py                        # FTSE experiment loop
│   ├── synthetic_runner.py              # Synthetic-data experiment loop
│   ├── generate_synthetic_data.py       # 5.6 Three sampling strategies (single/multi-topic, random)
│   ├── run_figure9_subsume.py           # 5.3 RQ2 retrieval-based FTSE on SubSumE
│   ├── run_figure12_variants.py        # Tech report: quality-function ablation
│   ├── run_figure13_relaxation.py      # 5.5 RQ3 relaxation analysis
│   ├── run_figure14_scalability.py     # 5.6 RQ4 scalability (3 strategies × 3 panels)
│   ├── run_table8_tpch.py              # 5.2 RQ1 TPC-H constraint satisfaction
│   ├── collect_memsum_bertsum_data.py  # 5.1 Generate input for PreSumm / MemSum
│   └── cnn_dailymail/                  # 5.1 CNN/DailyMail pipeline
│       ├── preprocess.py               #   Article → sentence-level JSON
│       ├── gpt4o_sentence_matcher.py   #   GPT-4o highlight → article sentences
│       └── README.md
├── data/
│   ├── README.md                        # Data setup instructions
│   ├── data_ctm.csv                     # SubSumE topic-scored sentences
│   ├── user_summary_jsons/              # SubSumE user examples (275 files)
│   ├── shared_docs/                     # state_indices.txt, stopwords.txt, StateDocuments/
│   └── cnn_dailymail/                   # Pre-processed CNN/DailyMail articles (pool of 200; paper uses 100 from ACL2020 split)
├── demo/                                # Section 6 — User study Flask app
│   ├── README.md
│   ├── server_code/                     # Flask backend + slider model
│   └── demo_site/                       # Older standalone demo
├── docs/
│   └── chatgpt_prompts.md               # §5.4 GPT-4o prompts (manual, file-attachment)
└── notebooks/
    └── results_analysis.ipynb           # Load .npz / .pkl and plot
```

Filenames retain `figure9` / `figure12` / `figure13` / `figure14` / `table8`
from an earlier draft of the paper for stability of imports. The mapping
to current paper subsections is in the [Paper ↔ code map](#paper--code-map)
below.

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

### RQ1 — §5.2 Constraint satisfaction performance (TPC-H)

```bash
python experiments/run_table8_tpch.py --db_path data/tpch.db --runs 5
```

Compares Ex2Bundle against Greedy and Random on the TPC-H supplier-selection
task and reports CSR (constraint satisfaction rate) and objective score.

### RQ2 — §5.3 Retrieval-based FTSE performance (SubSumE)

Run all three local baselines:
```bash
python experiments/run_figure9_subsume.py \
    --data_path   data/data_ctm.csv \
    --users_path  data/user_summary_jsons/ \
    --shared_docs data/shared_docs/ \
    --models      ex2bundle topk_sbert sudocu \
    --num_trials  2 --no_mp
```

For PreSumm / MemSum (both adapted with the same SBERT pre-filter):
```bash
# Step 1: pre-filter and dump input files for the external models
python experiments/collect_memsum_bertsum_data.py \
    --data_path   data/data_ctm.csv \
    --users_path  data/user_summary_jsons/ \
    --shared_docs data/shared_docs/ \
    --num_trials  2

# Step 2: run PreSumm (BertSumExt) / MemSum on the produced .story / .json
# files, then evaluate their snippets with utils/evaluation.py.
```

### RQ2 — §5.4 LLM-based summarization performance (ChatGPT-4o)

Two settings:

* **Focused intent (SubSumE).** Compare Ex2Bundle vs. ChatGPT-4o on 2 intents
  from SubSumE. Run `run_figure9_subsume.py` (above) for Ex2Bundle's numbers,
  and use the prompt in `docs/chatgpt_prompts.md` (SubSumE section) for the
  GPT-4o numbers.
* **Generic intent (CNN/DailyMail).** Compare Ex2Bundle vs. ChatGPT-4o across
  4 categories (Politics, Crime, Sports, Lifestyle). The paper draws 100
  articles from the ACL2020 split (avg 39 sentences/article); within each
  category, 5 articles are used as user examples and 3 as targets. Point
  `runner.py` at `data/cnn_dailymail/ACL2020_data/all_info/` (same JSON schema
  as SubSumE), and use the prompt in `docs/chatgpt_prompts.md` (CNN/DailyMail
  section) for the GPT-4o numbers.

ChatGPT-4o results were obtained manually via the GPT-4o web interface with
the target document attached as a file (not pasted inline) — no automated
runner is included.

### RQ3 — §5.5 Relaxation analysis

```bash
# Step 1: generate synthetic data (single-topic only — fastest)
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

The paper reports relaxation behavior on 50 target documents, varying
example sizes from 5 to 45 sentences.

### RQ4 — §5.6 Scalability analysis

```bash
# Step 1: generate ALL three sampling strategies (single-topic, multi-topic, random)
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

The paper reports scalability on CNN/DailyMail with example size $k$ varying
from 5 to 100 in increments of 5, using 5 source documents and 45 target
documents per setting.

### Tech report — quality-function ablation

The quality-function variants ablation (C-FREQ / BS / P-FREQ / TS / ALL) is
**moved to the technical report** in the current paper draft. The script is
still here for reproducibility:

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
| 5.1 Datasets | `data/`, `experiments/cnn_dailymail/` |
| 5.1 Top-k baseline | `models/sbert_baseline.py` |
| 5.1 SuDocu baseline | `models/sudocu_baseline.py` |
| 5.1 PreSumm / MemSum | `models/memsum_bertsum_collector.py` + `experiments/collect_memsum_bertsum_data.py` |
| 5.1 ChatGPT-4o | `docs/chatgpt_prompts.md` (manual queries, file attachment) |
| 5.2 RQ1 Constraint satisfaction (TPC-H) | `experiments/run_table8_tpch.py` |
| 5.3 RQ2 Retrieval-based FTSE (SubSumE) | `experiments/run_figure9_subsume.py` |
| 5.4 RQ2 LLM-based comparison (focused / generic intent) | `docs/chatgpt_prompts.md` + `experiments/runner.py` |
| 5.5 RQ3 Relaxation analysis | `experiments/run_figure13_relaxation.py` |
| 5.6 RQ4 Scalability (3 sampling strategies) | `experiments/run_figure14_scalability.py` + `generate_synthetic_data.py` |
| Tech report | `experiments/run_figure12_variants.py` (quality ablation) |
| 6 User study | `demo/` |

**ChatGPT-4o automation deliberately omitted.** The §5.4 GPT-4o numbers were
obtained manually via the GPT-4o web interface, providing the target document
as a file attachment (not pasted inline) along with the example summaries.
The prompts themselves are in `docs/chatgpt_prompts.md` for reproducibility,
but no API runner is included.

---

## Citation

If you use this software or build on the algorithm, please cite the paper.
See [CITATION.cff](CITATION.cff) for the full author list and citation entry.
