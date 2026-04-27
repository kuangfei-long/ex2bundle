"""
CNN/DailyMail preprocessing (Paper Section 5.1.2).

Splits each article into sentences, computes basic statistics, and writes
per-article sentence-level JSON files mirroring the SubSumE format:

  data/cnn_dailymail/raw_json/<article_id>.json:
      [{"sentenceNumber": 0, "sentenceText": "..."}, ...]

Inputs
------
- A CNN/DailyMail train.csv (with columns: id, article, highlights)

Usage
-----
python experiments/cnn_dailymail/preprocess.py \\
    --csv      data/cnn_dailymail/train.csv \\
    --output   data/cnn_dailymail/raw_json/ \\
    --max_articles 200
"""

import argparse
import json
import os

import nltk
import pandas as pd
from nltk.tokenize import sent_tokenize, word_tokenize


def main():
    nltk.download("punkt", quiet=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",          required=True)
    parser.add_argument("--output",       required=True, help="Output dir for per-article JSONs")
    parser.add_argument("--max_articles", type=int, default=200)
    parser.add_argument("--ids_file",     default=None, help="Optional: write list of IDs here")
    args = parser.parse_args()

    df = pd.read_csv(args.csv, nrows=args.max_articles)
    df["article_sentences"]    = df["article"].apply(sent_tokenize)
    df["highlights_sentences"] = df["highlights"].apply(sent_tokenize)
    df["article_word_count"]   = df["article"].apply(lambda x: len(word_tokenize(x)))
    df["highlights_word_count"]= df["highlights"].apply(lambda x: len(word_tokenize(x)))

    print(f"Loaded {len(df)} articles")
    print(f"  Avg article words:    {df['article_word_count'].mean():.1f}")
    print(f"  Avg highlights words: {df['highlights_word_count'].mean():.1f}")

    os.makedirs(args.output, exist_ok=True)
    for _, row in df.iterrows():
        records = [
            {"sentenceNumber": i, "sentenceText": s}
            for i, s in enumerate(row["article_sentences"])
        ]
        with open(os.path.join(args.output, f"{row['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    if args.ids_file:
        df["id"].to_csv(args.ids_file, index=False, header=False)
        print(f"  Wrote {args.ids_file}")

    print(f"Wrote {len(df)} per-article JSON files to {args.output}")


if __name__ == "__main__":
    main()
