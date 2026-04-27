"""
SBERT-based candidate-sentence prefilter.

Given the average SBERT embedding of the user's example summaries and a target
document, return the top-k most cosine-similar sentence ids. This shrinks the
candidate pool fed into the ILP and is shared with the SBERT baseline (where it
*is* the model).
"""

import json
import random
from os.path import join

import numpy as np
from scipy.spatial.distance import cosine


class Sentence_Prefilter_Wrapper:
    def __init__(self, shared_docs, nTopics):
        self.shared_docs_path = shared_docs
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            self.doc_indices = json.loads(f.read())
        self.nTopics = nTopics
        self.topic_names = ["topic_" + str(i) for i in range(self.nTopics)]

    def nearest_neighbor_bert_summary_filtering(
        self, avg_ex_embedding, test_doc, top_k, target_range=None
    ):
        file_path = join(
            self.shared_docs_path, "StateDocuments/", test_doc.strip() + "sudocu.npz"
        )
        test_doc_data = np.load(file_path)["embedding"]
        offset = self.doc_indices[test_doc][0]

        if target_range is not None:
            random.sample(range(target_range), target_range)  # preserved RNG behavior

        distances = [cosine(t, avg_ex_embedding) for t in test_doc_data]
        indices = np.argsort(distances)
        indices = [i + offset for i in indices]
        return indices[:top_k]
