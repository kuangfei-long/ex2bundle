"""
Figure 12: Quality-function ablation — run one Ex2Bundle variant at a time.

Supports all five objective modes defined in utils/quality.py:
  C-FREQ  — TF-IDF only
  BS      — SBERT cosine only
  P-FREQ  — TF-IDF + Log Probability Ratio
  TS      — Topic-score cosine only
  ALL     — Full objective (reproduces Figure 9 / Table 8 main result)

Usage
-----
# Run a single variant:
python experiments/run_figure12_variants.py \\
    --objective ALL \\
    --data_path data/data_ctm.csv \\
    --users_path data/user_summary_jsons/ \\
    --shared_docs data/shared_docs/ \\
    --no_mp

# Run all five variants in sequence:
for OBJ in C-FREQ BS P-FREQ TS ALL; do
    python experiments/run_figure12_variants.py --objective $OBJ ...
done
"""

import argparse
import logging
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
np.seterr(all="ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.runner import ExperimentRunner
from models.ex2bundle import Ex2Bundle
from utils.quality import VALID_OBJECTIVE_MODES


def main():
    parser = argparse.ArgumentParser(description="Figure 12 quality-function ablation")
    parser.add_argument("--objective", required=True, choices=VALID_OBJECTIVE_MODES,
                        help="Quality-function variant to evaluate")
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
    parser.add_argument("--no_mp", action="store_true")
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    runner = ExperimentRunner(
        num_examples=args.num_examples,
        num_test=args.num_test,
        users_path=args.users_path,
        data_path=args.data_path,
        nTopics=args.n_topics,
        min_range=args.min_range,
        max_index=args.max_range,
        shared_docs=args.shared_docs,
    )

    model_name = f"Ex2Bundle_{args.objective.replace('-', '_')}"
    runner.get_model_analysis(
        model_cls=Ex2Bundle,
        num_trials=args.num_trials,
        trial_start=args.trial_start,
        display_results=True,
        model_name=model_name,
        shared_docs_path=args.shared_docs,
        exp_folder="Figure12",
        multi_processing=not args.no_mp,
        model_kwargs={"objective_mode": args.objective},
    )


if __name__ == "__main__":
    main()
