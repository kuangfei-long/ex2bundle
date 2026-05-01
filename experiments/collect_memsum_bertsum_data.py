"""
Generate input files for PreSumm and MemSum baselines (Paper §5.1).

For each (intent, target_doc) pair in SubSumE, runs the SBERT pre-filter and
writes:

  Results/MemSumBertSumData/
  ├── bertsumex/                                # PreSumm (BertSumExt) input format
  │   └── ex_<i>_pool_<p>_trial_<t>.story
  ├── memsum_data_trail_<t>.json                # MemSum input format
  │     [{"text": [...], "summary": [...]}, ...]
  └── used_examples_trail_<t>.json              # Which examples were drawn

After running this, feed the .story files to PreSumm (BertSumExt) and the
.json file to MemSum to obtain their snippets, then evaluate them with the
same ROUGE / SBERT metrics used elsewhere.

Usage
-----
python experiments/collect_memsum_bertsum_data.py \\
    --data_path   data/data_ctm.csv \\
    --users_path  data/user_summary_jsons/ \\
    --shared_docs data/shared_docs/ \\
    --num_trials  2 \\
    --output_dir  experiments/Results/MemSumBertSumData/
"""

import argparse
import json
import logging
import os
import random
import sys
import warnings
from os.path import join

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.memsum_bertsum_collector import MemSumBertSumCollector
from utils.data_reader import UserDataReader

random.seed(7891)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path",   required=True)
    parser.add_argument("--users_path",  required=True)
    parser.add_argument("--shared_docs", required=True)
    parser.add_argument("--num_examples", type=int, default=3)
    parser.add_argument("--num_test",     type=int, default=5)
    parser.add_argument("--n_topics",     type=int, default=10)
    parser.add_argument("--min_range",    type=int, default=0)
    parser.add_argument("--max_range",    type=int, default=275)
    parser.add_argument("--num_trials",   type=int, default=2)
    parser.add_argument("--trial_start",  type=int, default=0)
    parser.add_argument("--output_dir",
                        default="experiments/Results/MemSumBertSumData")
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    udr = UserDataReader(args.users_path, args.data_path,
                         args.min_range, args.max_range)
    ground_truth, gt_indices = udr.read_summaries_list()
    intent_doc = np.array(udr.read_intent_doc())
    sudocu_data = np.array(udr.read_example_summaries_sudocu())
    ex_range = list(range(args.num_examples + args.num_test))

    bert_dir = join(args.output_dir, "bertsumex")
    os.makedirs(bert_dir, exist_ok=True)

    for trial in range(args.trial_start, args.num_trials):
        logging.info("Trial %d/%d", trial + 1, args.num_trials)

        collector = MemSumBertSumCollector(
            args.data_path, args.shared_docs, args.n_topics, args.num_examples,
        )
        memsum_summs = []
        used_examples = []

        for i, (intent, gt_list, gtidx_list, summaries) in enumerate(
            zip(intent_doc, ground_truth, gt_indices, sudocu_data)
        ):
            if i % 10 == 0:
                logging.info("  intent %d", i)

            documents = np.array(list(intent.values())[0])
            train_split = random.sample(range(len(summaries)), args.num_examples)
            test_idx = [j for j in ex_range if j not in train_split]
            example_set = summaries[train_split]
            test_docs = documents[np.array(test_idx)]
            test_gt = np.array(gt_list)[np.array(test_idx)]
            test_gt_idx = np.array(gtidx_list, dtype=object)[np.array(test_idx)]

            used_examples.append(example_set.tolist())

            for p, (doc, gt_text, gt_idxs) in enumerate(zip(test_docs, test_gt, test_gt_idx)):
                pred_sentences, pred_ids = collector.get_predicted_summary(
                    doc, example_set.tolist(),
                )

                # BertSumExt: .story file
                story = " ".join(pred_sentences) + "\n\n@highlight\n\n" + str(gt_text)
                fname = f"ex_{i}_pool_{p}_trial_{trial}.story"
                with open(join(bert_dir, fname), "w") as f:
                    f.write(story)

                # MemSum: append entry
                memsum_summs.append({
                    "text":    list(pred_sentences),
                    "summary": list(np.array(collector.df["sentence"])
                                    [np.array(gt_idxs, dtype=int)]),
                })

        with open(join(args.output_dir, f"memsum_data_trail_{trial}.json"), "w") as f:
            json.dump(memsum_summs, f)
        with open(join(args.output_dir, f"used_examples_trail_{trial}.json"), "w") as f:
            json.dump(used_examples, f)

        logging.info("Saved trial %d → %s", trial, args.output_dir)


if __name__ == "__main__":
    main()
