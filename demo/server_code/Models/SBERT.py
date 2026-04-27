from .Model import Model
from abc import abstractmethod
import pandas as pd
import numpy as np
from os.path import join
from ..utils.filtering import Sentence_Prefilter_Wrapper

class SBERT(Model):

    def __init__(self, data_path, shared_docs_path, nTopics):
        super().__init__(data_path, shared_docs_path, nTopics)
        self.filter_obj = Sentence_Prefilter_Wrapper(data_path, shared_docs_path, nTopics)
        self.df = pd.read_csv(data_path, sep=";")

    def get_predicted_summary(self, target_doc, example_summaires, processed_ctr, bounds=None, first_gen=False):
        summary_indicies = self.filter_obj.nearest_neighbor_bert_summary_filtering(example_summaries=example_summaires, test_doc=target_doc, top_k=10)
        sentences = self.df[(self.df['name'] == target_doc) & (self.df['sid'].isin(summary_indicies))]['sentence'].to_numpy().tolist()

        return (" ".join(sentences), summary_indicies)