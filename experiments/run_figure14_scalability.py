"""
RQ4: Scalability analysis — Paper §5.6.

Reproduces the three-panel × three-curve plot from the paper:

  Panels:    (a) Learning time   (b) Retrieval time   (c) Total time
  Curves:    single-topic, random, multi-topic  (sampling strategies)

Workflow
--------
1. Run ``generate_synthetic_data.py --strategy all`` once to produce
   ``data/synthetic_data_collection/{single,random,multi}/topic*/...``
2. Run this script — it iterates over all three strategy folders, calls
   ``SyntheticExperimentRunner`` for each, and combines the resulting pkls
   into a single 3-curve × 3-panel plot.

Usage
-----
python experiments/run_figure14_scalability.py \\
    --data_path       data/data_ctm.csv \\
    --shared_docs     data/shared_docs/ \\
    --synthetic_root  data/synthetic_data_collection/ \\
    --states_file     data/shared_docs/just_states.txt \\
    --results_path    results/Figure14/
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
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.synthetic_runner import SyntheticExperimentRunner
from models.ex2bundle import Ex2Bundle


STRATEGIES = ("single", "random", "multi")
STRATEGY_LABEL = {
    "single": "Single-feature",
    "random": "Random",
    "multi":  "Multi-feature",
}
STRATEGY_COLOR = {
    "single": "tab:blue",
    "random": "tab:orange",
    "multi":  "tab:green",
}


def run_one_strategy(args, strategy, out_dir):
    pkl_path = os.path.join(out_dir, "evaluation_data.pkl")
    if os.path.exists(pkl_path):
        logging.info("[%s] reusing existing pkl: %s", strategy, pkl_path)
        with open(pkl_path, "rb") as f:
            return pickle.load(f)

    parent = os.path.join(args.synthetic_root, strategy)
    if not os.path.isdir(parent):
        raise FileNotFoundError(
            f"Strategy folder {parent} not found. Run generate_synthetic_data.py first."
        )

    os.makedirs(out_dir, exist_ok=True)
    runner = SyntheticExperimentRunner(
        num_examples=args.num_examples,
        num_test=45,
        users_path=parent,
        data_path=args.data_path,
        nTopics=args.n_topics,
        min_range=0,
        max_index=50,
        shared_docs=args.shared_docs,
        results_path=out_dir,
        states_file=args.states_file,
    )
    runner.model_get_evaluation(Ex2Bundle, parent, num_test_docs=args.num_test_docs)
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def plot_three_panel(all_data, results_path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))

    panel_keys = [
        ("all_avg_learning_times_per_sentence_len",  "(a) Learning"),
        ("all_avg_retrieval_times_per_sentence_len", "(b) Retrieval"),
        ("__total__",                                "(c) Total"),
    ]

    for ax, (key, title) in zip(axes, panel_keys):
        for strategy in STRATEGIES:
            d = all_data.get(strategy)
            if d is None:
                continue
            x = d["x_values"]
            if key == "__total__":
                learn = d["all_avg_learning_times_per_sentence_len"]
                retr  = d["all_avg_retrieval_times_per_sentence_len"]
                n = min(len(learn), len(retr), len(x))
                y = [learn[i] + retr[i] for i in range(n)]
                ax.plot(x[:n], y, "o-", color=STRATEGY_COLOR[strategy],
                        label=STRATEGY_LABEL[strategy])
            else:
                y = d[key]
                ax.plot(x[:len(y)], y, "o-", color=STRATEGY_COLOR[strategy],
                        label=STRATEGY_LABEL[strategy])
        ax.set_xlabel("Number of sentences (k)")
        ax.set_ylabel("Time (sec)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

    plt.suptitle("Figure 14: Scalability of Ex2Bundle", y=1.02)
    plt.tight_layout()
    out = os.path.join(results_path, "fig14_three_panel.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logging.info("Figure 14 saved to %s", out)


def main():
    parser = argparse.ArgumentParser(description="Figure 14 scalability (3 strategies × 3 panels)")
    parser.add_argument("--data_path",      required=True)
    parser.add_argument("--shared_docs",    required=True)
    parser.add_argument("--synthetic_root", required=True,
                        help="Folder containing single/, random/, multi/ subfolders")
    parser.add_argument("--states_file",    required=True)
    parser.add_argument("--results_path",   default="results/Figure14")
    parser.add_argument("--num_examples",   type=int, default=5)
    parser.add_argument("--n_topics",       type=int, default=10)
    parser.add_argument("--num_test_docs",  type=int, default=5)
    parser.add_argument("--strategies", nargs="+", default=list(STRATEGIES),
                        choices=list(STRATEGIES))
    parser.add_argument("--log", default="INFO")
    args = parser.parse_args()

    os.makedirs(args.results_path, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, args.log.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    all_data = {}
    for strategy in args.strategies:
        out_dir = os.path.join(args.results_path, strategy)
        try:
            all_data[strategy] = run_one_strategy(args, strategy, out_dir)
        except Exception:
            logging.exception("Strategy %s failed", strategy)

    if all_data:
        plot_three_panel(all_data, args.results_path)
    else:
        logging.error("No strategies completed successfully")


if __name__ == "__main__":
    main()
