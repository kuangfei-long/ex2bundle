"""
GPT-4o reverse sentence matcher for CNN/DailyMail (Paper Section 5.1.2).

The paper says:

   "We use the highlights as reference summaries and use ChatGPT-4o to identify
    the corresponding sentences in the original articles that best match these
    highlights."

This script implements that step. For each article × highlight pair, GPT-4o is
asked to:

  Q1. Label the article topic (sports / daily news / entertainment / economy /
      politic / other) — used to bucket the results into Table 11 categories.
  Q2. Tokenize the article into numbered sentences.
  Q3. Pick which sentences best support the highlight.
  Q4. Return the IDs of those sentences.

Output: ``all_info_<split>.json`` matching the schema produced by Oscar's
``GPT_ACL.py``:

  [{"id": ..., "name": "CNNDM_<i>",
    "original_text": ..., "original_summary": ...,
    "GPT_topic": "...", "GPT_raw_json": [...],
    "GPT_setences": [...], "GPT_sentence_ids": [...]}, ...]

Requires: ``OPENAI_API_KEY`` env var; ``openai>=1.0`` Python client.

Usage
-----
python experiments/cnn_dailymail/gpt4o_sentence_matcher.py \\
    --jsonl      data/cnn_dailymail/train_CNNDM_roberta.jsonl \\
    --output     data/cnn_dailymail/ACL2020_data/all_info/all_train_CNNDM_roberta.json \\
    --num_lines  20
"""

import argparse
import json
import os

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


TOPICS = ["sports", "daily news", "entertainment", "economy", "politic", "other"]


def build_messages(text, summary):
    return [
        {"role": "system", "content": (
            f"You are an assistant. I will ask you series of questions. "
            f"Put question answers separately in a JSON format, where keys are Q1, Q2, ...\n"
            f"And I will give some input as follows, please remember them:\n"
            f"topics_array: {TOPICS}\n"
            f"text: {text}\n"
            f"summary: {summary}\n"
            f"Make sure the output can be used in json.loads() and is wrapped in "
            f"three quotation marks and the word json."
        )},
        {"role": "user", "content": "Q1. Label the text/summary to one of the topics. Return a string."},
        {"role": "user", "content":
            "Q2. Use punkt and actual meaning to parse the original article text "
            "to sentence-level and get indices starting at 0. Make sure the "
            "sentenceText is a valid string inside double quotation marks. "
            "Return JSON list format like:\n"
            "[{\"sentenceNumber\": 0, \"sentenceText\": \"This is example sentence 0.\"}, ...]"
        },
        {"role": "user", "content":
            "Q3. Select the relevant sentences to the summary from the text. "
            "Put them in a sentence list."},
        {"role": "user", "content":
            "Q4. Return a list with the sentence ID of each selected summary sentence."},
    ]


def parse_response(raw):
    cleaned = raw.strip("`").strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl",     required=True,
                        help="JSONL input with {text, summary} per line")
    parser.add_argument("--output",    required=True)
    parser.add_argument("--num_lines", type=int, default=20)
    parser.add_argument("--model",     default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    if not _HAS_OPENAI:
        raise SystemExit("openai package not installed; pip install openai>=1.0")
    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("OPENAI_API_KEY env var must be set")

    client = OpenAI()
    all_info = []

    with open(args.jsonl) as f:
        for i in range(args.num_lines):
            line = f.readline()
            if not line:
                break
            data = json.loads(line)
            text, summary = data["text"], data["summary"]
            print(f"[{i+1}/{args.num_lines}] Querying GPT-4o…", flush=True)

            try:
                resp = client.chat.completions.create(
                    model=args.model,
                    temperature=args.temperature,
                    messages=build_messages(text, summary),
                )
                ans = parse_response(resp.choices[0].message.content)
                all_info.append({
                    "id": i,
                    "name": f"CNNDM_roberta_{i}",
                    "original_text":    text,
                    "original_summary": summary,
                    "GPT_topic":        ans.get("Q1", "other"),
                    "GPT_raw_json":     ans.get("Q2", []),
                    "GPT_setences":     ans.get("Q3", []),
                    "GPT_sentence_ids": ans.get("Q4", []),
                })
            except Exception as e:
                print(f"  failed on article {i}: {e}", flush=True)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_info, f, indent=2)
    print(f"Wrote {len(all_info)} matched articles to {args.output}")


if __name__ == "__main__":
    main()
