# CNN/DailyMail pipeline

Used for **Table 11** (Section 5.4 generic-intent retrieval comparison with
ChatGPT-4o) and as an alternative dataset for the **Figure 14** scalability
analysis (Section 5.7).

## Workflow

```
                      cnn_dailymail/train.csv  (raw)
                                │
                                ▼
                    preprocess.py              ──► raw_json/<id>.json (per-article)
                                │
                                ▼
              gpt4o_sentence_matcher.py        ──► all_info_<split>.json
                  (uses GPT-4o to map highlights              │
                   back to article sentences)                 │
                                                              ▼
                                              Treated as "user examples" by
                                              the standard ExperimentRunner.
```

## Steps

### 1. Sentence-tokenize each article
```bash
python experiments/cnn_dailymail/preprocess.py \
    --csv          data/cnn_dailymail/train.csv \
    --output       data/cnn_dailymail/raw_json/ \
    --max_articles 200
```

### 2. GPT-4o reverse matching (highlight → article sentences)
Requires `OPENAI_API_KEY` in env. Costs depend on `--num_lines`.

```bash
python experiments/cnn_dailymail/gpt4o_sentence_matcher.py \
    --jsonl     data/cnn_dailymail/train_CNNDM_roberta.jsonl \
    --output    data/cnn_dailymail/ACL2020_data/all_info/all_train_CNNDM_roberta.json \
    --num_lines 200
```

### 3. Use the resulting JSON as "examples"
The output `all_info_*.json` follows the same schema as SubSumE's
`userInput_*.txt`, so you can plug it into `experiments/runner.py` directly
by pointing `--users_path` at the folder.

## Pre-shipped artifacts

We ship the already-processed copies under `data/cnn_dailymail/`:

```
data/cnn_dailymail/
├── raw_json/              # 200 pre-tokenized article JSONs
├── mail_id.txt            # corresponding article IDs
└── ACL2020_data/
    └── all_info/
        ├── all_train_CNNDM_roberta.json
        └── all_CNNDM_roberta.json
```

If you want to skip steps 1–2, use these directly.
