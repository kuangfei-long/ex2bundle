"""
RQ2: Figure 9 — full baseline comparison on SubSumE.

Runs ROUGE / SBERT / topic-score-diff comparison across:
  - Ex2Bundle    (our system)
  - Top-k SBERT  (sBert baseline, paper Section 5.1.3)
  - SuDocu       (LDA + simple fixed-step relaxation, [11])
  - MemSum / BertSumExt — these baselines need external inference and are NOT
    run here. Use ``collect_memsum_bertsum_data.py`` to produce their input
    files, run the external models on those files, then evaluate the resulting
    summaries with the same ROUGE/SBERT functions in ``utils/evaluation.py``.
  - ChatGPT-4o was queried manually (Tables 10/11) — no script.

Usage
-----
# All three local baselines:
python experiments/run_figure9_subsume.py \\
    --data_path   data/data_ctm.csv \\
    --users_path  data/user_summary_jsons/ \\
    --shared_docs data/shared_docs/ \\
    --models      ex2bundle topk_sbert sudocu \\
    --num_trials  2 \\
    --no_mp

# Just one model:
python experiments/run_figure9_subsume.py ... --models ex2bundle
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
from models.sbert_baseline import SBERTTopK
from models.sudocu_baseline import SuDocuBaseline


MODEL_REGISTRY = {
    "ex2bundle":   (Ex2Bundle,      "Ex2Bundle"),
    "topk_sbert":  (SBERTTopK,      "TopK_SBERT"),
    "sudocu":      (SuDocuBaseline, "SuDocu_baseline"),
}


def main():
    parser = argparse.ArgumentParser(description="Run Figure 9 SubSumE baselines")
    parser.add_argument("--data_path",   required=True)
    parser.add_argument("--users_path",  required=True)
    parser.add_argument("--shared_docs", required=True)
    parser.add_argument("--models", nargs="+", default=["ex2bundle"],
                        choices=list(MODEL_REGISTRY.keys()))
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

    for key in args.models:
        cls, name = MODEL_REGISTRY[key]
        logging.info("==== Running %s ====", name)
        runner.get_model_analysis(
            model_cls=cls,
            num_trials=args.num_trials,
            trial_start=args.trial_start,
            display_results=True,
            model_name=name,
            shared_docs_path=args.shared_docs,
            exp_folder="Figure9",
            multi_processing=not args.no_mp,
        )


if __name__ == "__main__":
    main()
