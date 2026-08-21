# Data

This directory holds runtime data files that are **not** committed to the repo
due to size. Copy them here from the original source branches before running
any experiment.

---

## Required files

### SubSumE experiments (§5.3 retrieval-based FTSE, §5.5 relaxation, §5.6 scalability, and the tech-report quality-function ablation)

```
data/
├── data_ctm.csv                      # topic-scored sentence database (CSV, ';'-separated)
├── user_summary_jsons/               # SubSumE user summaries
│   └── userInput_0.txt … userInput_274.txt
└── shared_docs/
    ├── state_indices.txt             # JSON: {"statename": [start_idx, end_idx], …}
    ├── stopwords.txt                 # one stopword per line
    ├── just_states.txt               # one US state name per line (50 lines)
    └── StateDocuments/
        └── <statename>sudocu.npz     # SBERT sentence embeddings, key="embedding"
```

Copy from the source branches:
```bash
# data_ctm.csv — lives in:
#   Source/user_study_code/server_code/flask_code/data_ctm.csv
# shared_docs/  — lives in:
#   Source/user_study_code/server_code/flask_code/data/
# user_summary_jsons/ — lives in:
#   Source/SubSumE_Data/user_summary_jsons/
```

### Synthetic data (§5.5 relaxation, §5.6 scalability)

Generate with:
```bash
python experiments/generate_synthetic_data.py \
    --data_csv    data/data_ctm.csv \
    --states_file data/shared_docs/just_states.txt \
    --output_dir  data/synthetic_data_collection/
```

### TPC-H (§5.2 RQ1 constraint satisfaction)

Unlike the files above, the TPC-H database **is committed**: `data/tpch.db` is a
ready-to-use scale-factor 0.01 instance (100 suppliers, 25 nations, 8000
partsupp rows) exposing the `SupplierFeatures` view the experiment reads. No
setup needed — just run the experiment.

The full schema (base tables + the feature-view definitions used for the paper's
Table 8) is documented in [`tpch_schema.sql`](tpch_schema.sql). To regenerate
the DB from scratch, generate SF-0.01 tables with the
[TPC-H dbgen](https://www.tpc.org/tpch/) tool, load `supplier.tbl` /
`nation.tbl` / `partsupp.tbl`, then:
```bash
sqlite3 data/tpch.db < data/tpch_schema.sql
```

---

## data_ctm.csv schema

| Column     | Type    | Description                           |
|------------|---------|---------------------------------------|
| `name`     | string  | US state name (lowercase)             |
| `sentence` | string  | Raw sentence text                     |
| `sid`      | int     | Global sentence ID (0-indexed)        |
| `topic_0` … `topic_9` | float | CTM topic score for each topic |

Separator is `;` (not `,`).

## user_summary_jsons schema

Each `userInput_<N>.txt` is a JSON with keys:
```json
{
  "intent": "...",
  "summaries": [
    {
      "state_name": "...",
      "sentence_ids": [...],
      "sentences": [...],
      "used_keywords": [...]
    }
  ]
}
```

## StateDocuments/*.npz

Each `.npz` file has one key `"embedding"` with shape `(num_sentences, 768)`,
containing `all-mpnet-base-v2` SBERT embeddings for every sentence in that
state document. Row `i` corresponds to sentence `i` relative to the start
index stored in `state_indices.txt`.
