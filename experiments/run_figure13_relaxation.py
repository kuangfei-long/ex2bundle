"""
RQ3: Bound-relaxation experiment — Figure 13.

Uses SyntheticExperimentRunner to measure how often (and how many topics)
the ConflictRefiner-based relaxation fires as the example-summary length varies
from 5 to 45 sentences (step 5).

Run `generate_synthetic_data.py` first to populate the data directory.

Usage
-----
python experiments/run_figure13_relaxation.py \\
    --data_path       data/data_ctm.csv \\
    --shared_docs     data/shared_docs/ \\
    --synthetic_data  data/synthetic_data_collection/ \\
    --states_file     data/shared_docs/just_states.txt \\
    --results_path    results/Figure13/
"""

import argparse
import logging
import os
import pickle
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.synthetic_runner import SyntheticExperimentRunner
from models.ex2bundle import Ex2Bundle


def plot_relaxation(results, results_path):
    x = results["x_values"]

    # Avg relaxation frequency
    avg_relax = results["all_avg_relax_freqs_per_sentence_len"]
    if avg_relax:
        plt.figure(figsize=(10, 5))
        plt.plot(x[:len(avg_relax)], avg_relax, "o-", color="orange")
        plt.xlabel("Num sentences in example summary")
        plt.ylabel("Avg Relaxation Frequency")
        plt.title("Avg Relaxation Frequency vs Example Summary Length (Figure 13)")
        plt.xticks(x)
        plt.tight_layout()
        plt.savefig(os.path.join(results_path, "fig13_avg_relax_freq.png"), dpi=150)
        plt.close()

    # Per-instance relaxation counts (strip plot)
    all_relax = results["all_relax_freqs_per_sentence_len"]
    all_ntopics = results["all_num_relaxed_topics_per_sentence_len"]
    if any(all_relax):
        freqs_df = pd.DataFrame({
            "Example Summary Length": sum(
                [[x[i]] * len(v) for i, v in enumerate(all_relax)], []
            ),
            "Relaxation Frequency": sum(all_relax, []),
        })
        plt.figure(figsize=(10, 5))
        sns.stripplot(x="Example Summary Length", y="Relaxation Frequency",
                      data=freqs_df, jitter=True, color="orange")
        plt.title("Relaxation Count Variation (Figure 13)")
        plt.tight_layout()
        plt.savefig(os.path.join(results_path, "fig13_relax_freq_variation.png"), dpi=150)
        plt.close()

    if any(all_ntopics):
        topics_df = pd.DataFrame({
            "Example Summary Length": sum(
                [[x[i]] * len(v) for i, v in enumerate(all_ntopics)], []
            ),
            "Num Topics Relaxed": sum(all_ntopics, []),
        })
        plt.figure(figsize=(10, 5))
        sns.stripplot(x="Example Summary Length", y="Num Topics Relaxed",
                      data=topics_df, jitter=True, color="purple")
        plt.title("Num Topics Relaxed (Figure 13)")
        plt.tight_layout()
        plt.savefig(os.path.join(results_path, "fig13_num_topics_relaxed.png"), dpi=150)
        plt.close()

    logging.info("Figure 13 plots saved to %s", results_path)


def main():
    parser = argparse.ArgumentParser(description="Figure 13 relaxation experiment")
    parser.add_argument("--data_path",      required=True)
    parser.add_argument("--shared_docs",    required=True)
    parser.add_argument("--synthetic_data", required=True,
                        help="Parent folder with topic0/ … topic9/ subfolders")
    parser.add_argument("--states_file",    required=True,
                        help="just_states.txt — one state name per line")
    parser.add_argument("--results_path",   default="results/Figure13")
    parser.add_argument("--num_examples",   type=int, default=5)
    parser.add_argument("--n_topics",       type=int, default=10)
    parser.add_argument("--num_test_docs",  type=int, default=5)
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--pkl_only", action="store_true",
                        help="Skip plotting; only (re)generate the pkl data file")
    args = parser.parse_args()

    os.makedirs(args.results_path, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    pkl_path = os.path.join(args.results_path, "evaluation_data.pkl")

    if not os.path.exists(pkl_path):
        runner = SyntheticExperimentRunner(
            num_examples=args.num_examples,
            num_test=45,
            users_path=args.synthetic_data,
            data_path=args.data_path,
            nTopics=args.n_topics,
            min_range=0,
            max_index=50,
            shared_docs=args.shared_docs,
            results_path=args.results_path,
            states_file=args.states_file,
        )
        runner.model_get_evaluation(Ex2Bundle, args.synthetic_data,
                                    num_test_docs=args.num_test_docs)

    if args.pkl_only:
        return

    with open(pkl_path, "rb") as f:
        results = pickle.load(f)

    plot_relaxation(results, args.results_path)


if __name__ == "__main__":
    main()
