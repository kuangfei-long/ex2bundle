"""
Abstract Model base class + SuDocuBase that implements bound synthesis.

Bound synthesis (Paper Section 4.1.1) lives in `SuDocuBase.get_bounds`:
  given a list of example summaries, sum each topic's per-sentence scores within
  each summary, take the per-topic min/max across summaries, then pad with
  +/- 10% as the initial constraint bounds.
"""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Model(ABC):
    """Common interface for both Ex2Bundle and the baselines."""

    def __init__(self, data_path, shared_docs_path, num_examples, nTopics, is_generative):
        self.data_path = data_path
        self.shared_docs_path = shared_docs_path
        self.num_examples = num_examples
        self.nTopics = nTopics
        self.is_generative = is_generative

    @abstractmethod
    def get_predicted_summary(self, target_doc, example_summaries, *args, **kwargs):
        ...


class SuDocuBase(Model):
    """Loads the topic-scored CSV and synthesizes intent bounds from examples."""

    def __init__(self, data_path, shared_docs_path, nTopics, num_examples, is_generative,
                 time_limit=100):
        super().__init__(data_path, shared_docs_path, num_examples, nTopics, is_generative)
        self.data_path = data_path
        self.shared_docs_path = shared_docs_path
        self.nTopics = nTopics
        self.num_examples = num_examples

        # Auto-detect separator: ';' or ','
        with open(self.data_path) as f:
            sep = ';' if ';' in f.readline() else ','
        self.df = pd.read_csv(self.data_path, sep=sep)
        self.time_limit = time_limit
        self.topic_names = np.array(['topic_' + str(i) for i in range(self.nTopics)])

    def get_avg_summaries_length(self, example_summaires):
        n = 0.0
        for ex in example_summaires:
            n += float(len([int(s) for s in ex["sentence_ids"]]))
        return n / len(example_summaires)

    def get_bounds(self, example_summaires):
        """Bound synthesis, Paper Section 4.1.1.

        Returns
          bounds : np.ndarray, shape (nTopics, 2). bounds[j] = (lb_j, ub_j)
          avg_sum_len : float. Average example summary length (number of sentences).
        """
        topic_sums = np.zeros((len(example_summaires), self.nTopics))
        avg_len = 0.0

        for i, ex in enumerate(example_summaires):
            sentence_ids = [int(s) for s in ex["sentence_ids"]]
            avg_len += float(len(sentence_ids))
            for tid in range(self.nTopics):
                topic_sums[i, tid] = np.sum([
                    np.array(self.df[self.df["sid"] == sid]["topic_" + str(tid)])[0]
                    for sid in sentence_ids
                ])

        topic_min = list(np.min(topic_sums, axis=0))
        topic_max = list(np.max(topic_sums, axis=0))
        avg_len = avg_len / len(example_summaires)

        bounds = np.zeros((self.nTopics, 2))
        eps = 1e-4
        for i in range(len(topic_min)):
            bounds[i, 0] = round(topic_min[i] * 0.9 - eps, 4)
            bounds[i, 1] = round(topic_max[i] * 1.1 + eps, 4)

        assert bounds.shape == (self.nTopics, 2), "bounds shape mismatch"
        return bounds, avg_len
