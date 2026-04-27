"""
Top-k SBERT baseline (Paper Section 5.1.3).

Selects the top-k most cosine-similar sentences in the target document w.r.t.
the average SBERT embedding of the user's example summaries, where k is the
average example summary length. No ILP, no constraints -- a pure retrieval
baseline.
"""

import pandas as pd

from models.base import Model
from utils.filtering import Sentence_Prefilter_Wrapper
from utils.quality import Objective_Function_Wrapper


class SBERTTopK(Model):
    def __init__(self, data_path, shared_docs_path, nTopics, num_examples, is_generative=False):
        super().__init__(data_path, shared_docs_path, num_examples, nTopics, is_generative)
        with open(data_path) as f:
            sep = ';' if ';' in f.readline() else ','
        self.df = pd.read_csv(data_path, sep=sep)
        self.filter_obj = Sentence_Prefilter_Wrapper(shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(shared_docs_path, nTopics)

    def get_predicted_summary(self, target_doc, example_summaries, processed_ctr=None, bounds=None):
        avg_len = 0.0
        for ex in example_summaries:
            avg_len += float(len([int(s) for s in ex["sentence_ids"]]))
        avg_len /= len(example_summaries)

        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaries)
        summary_indices = self.filter_obj.nearest_neighbor_bert_summary_filtering(
            avg_ex_embedding=ex_embedding, test_doc=target_doc, top_k=int(avg_len),
        )
        sentences = self.df[
            (self.df['name'] == target_doc) & (self.df['sid'].isin(summary_indices))
        ]['sentence'].to_numpy().tolist()
        return (" ".join(sentences), summary_indices)
