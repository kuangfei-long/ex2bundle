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


class Sentence_Prefilter_Wrapper:
    def __init__(self, shared_docs, nTopics):
        self.shared_docs_path = shared_docs
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            self.doc_indices = json.loads(f.read())
        self.nTopics = nTopics
        self.topic_names = ["topic_" + str(i) for i in range(self.nTopics)]
        # test_doc's <state>sudocu.npz otherwise gets reloaded from disk on
        # every single call -- a scan reuses the same handful of states
        # across many calls, so this cache (keyed by file_path, mmap'd) turns
        # repeated full-file reads into one load per state. Same fix as
        # revision/filtering.py's _npz_cache, ported here without that file's
        # non-contiguous-sid/oversized-npz handling, which only matters for
        # revision/extend_embeddings.py-patched npz files this module's
        # callers (SBERT baseline, sudocu baseline, etc.) never touch.
        self._npz_cache = {}

    def nearest_neighbor_bert_summary_filtering(
        self, avg_ex_embedding, test_doc, top_k, target_range=None
    ):
        file_path = join(
            self.shared_docs_path, "StateDocuments/", test_doc.strip() + "sudocu.npz"
        )
        if file_path in self._npz_cache:
            test_doc_data = self._npz_cache[file_path]
        else:
            test_doc_data = np.load(file_path, mmap_mode="r")["embedding"]
            self._npz_cache[file_path] = test_doc_data
        offset = self.doc_indices[test_doc][0]

        if target_range is not None:
            random.sample(range(target_range), target_range)  # preserved RNG behavior

        # Vectorized cosine distance (1 - cosine similarity, matching
        # scipy.spatial.distance.cosine's definition exactly) against every
        # row of test_doc_data at once, instead of a Python-level loop calling
        # scipy's cosine() once per row -- see revision/filtering.py's fork of
        # this same function for the timing instrumentation that traced a
        # multi-second-per-call cost to exactly this loop.
        doc_norms = np.linalg.norm(test_doc_data, axis=1)
        query_norm = np.linalg.norm(avg_ex_embedding)
        similarities = (test_doc_data @ avg_ex_embedding) / (doc_norms * query_norm)
        distances = 1.0 - similarities
        indices = np.argsort(distances)
        indices = [i + offset for i in indices]
        return indices[:top_k]
