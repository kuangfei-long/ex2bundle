"""
MemSum / BertSumExt data collector (Paper Section 5.1.3).

The paper compares against MemSum [15] and BertSumExt [27], neither of which
natively supports example-driven extraction. Following Oscar's protocol, we:

  1. Pre-filter the target document with the same SBERT prefilter Ex2Bundle uses.
  2. Pass the pre-filtered sentences to MemSum / BertSumExt for extractive
     summarization, treating those models as black boxes.

This file only implements step (1): given a target document and example
summaries, return the SBERT-pre-filtered sentence pool. The output is
collected by ``experiments/collect_memsum_bertsum_data.py`` into the file
formats required by each external model:

  - BertSumExt: ``.story`` files with the format
        <space-joined predicted sentences>\\n\\n@highlight\\n\\n<gt summary>
  - MemSum: a single ``memsum_data_trail_<i>.json`` with entries
        {"text": [pre-filtered sentences],
         "summary": [ground-truth sentences]}
"""

import numpy as np
import pandas as pd

from models.base import Model
from utils.filtering import Sentence_Prefilter_Wrapper
from utils.quality import Objective_Function_Wrapper


class MemSumBertSumCollector(Model):
    """SBERT pre-filter wrapper used to feed MemSum / BertSumExt."""

    def __init__(self, data_path, shared_docs_path, nTopics, num_examples,
                 is_generative=False, length_modifier=0.25, pool_mult=10, pool_cap=100):
        super().__init__(data_path, shared_docs_path, num_examples, nTopics, is_generative)
        with open(data_path) as f:
            sep = ";" if ";" in f.readline() else ","
        self.df = pd.read_csv(data_path, sep=sep)
        self.filter_obj = Sentence_Prefilter_Wrapper(shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(shared_docs_path, nTopics)
        self.length_modifier = length_modifier
        self.pool_mult = pool_mult
        self.pool_cap = pool_cap

    def get_predicted_summary(self, target_doc, example_summaries, bounds=None):
        avg_len = 0.0
        for ex in example_summaries:
            avg_len += float(len([int(s) for s in ex["sentence_ids"]]))
        avg_len /= len(example_summaries)

        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaries)
        pool_size = min(int(avg_len * self.pool_mult), self.pool_cap)

        filtered_ids = self.filter_obj.nearest_neighbor_bert_summary_filtering(
            avg_ex_embedding=ex_embedding, test_doc=target_doc, top_k=pool_size,
        )
        target_df = self.df[
            (self.df["name"] == target_doc) & (self.df["sid"].isin(filtered_ids))
        ]
        sentences = target_df["sentence"].to_numpy()
        sentence_ids = target_df["sid"].to_numpy()
        return sentences, sentence_ids
