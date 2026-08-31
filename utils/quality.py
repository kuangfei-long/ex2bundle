"""
Quality function variants for the Ex2Bundle objective (Section 4.2, Figure 12).

Four variants are supported:
  - "C-FREQ"  (default): TF-IDF score, term-frequency based on user examples.
  - "BS"     : SBERT cosine similarity between target sentence and example summaries.
  - "P-FREQ" : TF-IDF + Log Probability Ratio (positional / probabilistic frequency).
  - "TS"     : Topic-distribution cosine similarity.

`combine_scores(...)` returns the per-sentence quality scores used as ILP coefficients.
"""

import math
import json
import re
import string
import itertools
from os.path import join

import numpy as np
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import minmax_scale


VALID_OBJECTIVE_MODES = ("C-FREQ", "BS", "P-FREQ", "TS", "ALL")


class Objective_Function_Wrapper:
    """Computes per-sentence quality scores used by the Ex2Bundle ILP objective."""

    def __init__(self, shared_docs, nTopics):
        self.shared_docs_path = shared_docs
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            self.doc_indicies = json.loads(f.read())
        self.nTopics = nTopics
        self.topic_names = ["topic_" + str(i) for i in range(self.nTopics)]
        # calculateBSMeritScore/get_ex_embedding both reload a state's
        # <state>sudocu.npz from disk on every single call otherwise -- a
        # scan reuses the same handful of states across many
        # get_predicted_summary calls, so this cache (keyed by npz_path,
        # mmap'd) turns repeated full-file reads into one load per state.
        # Same fix as revision/quality.py's _npz_cache, ported here without
        # that file's non-contiguous-sid ("sids" array) handling, which only
        # matters for revision/extend_embeddings.py-patched npz files that
        # models/ex2bundle.py never touches.
        self._npz_cache = {}

    # -- text cleaning ---------------------------------------------------------
    def cleanSentences(self, sentences):
        with open(self.shared_docs_path + "stopwords.txt") as f:
            stopwords2 = [l.strip().lower() for l in f.readlines() if l.strip()]
        sentences = [str(s).lower() for s in sentences]
        table = str.maketrans('', '', string.punctuation)
        sentences = [s.translate(table) for s in sentences]
        sentences = [re.sub(r'\d+', 'num', s) for s in sentences]
        stopwords = set(nltk.corpus.stopwords.words('english') + stopwords2)
        sentences = [[w for w in s.split() if w not in stopwords] for s in sentences]
        stemmer = nltk.stem.PorterStemmer()
        return [" ".join([stemmer.stem(w) for w in s]) for s in sentences]

    # -- BS: SBERT cosine similarity -------------------------------------------
    def calculateBSMeritScore(self, sentence_ids, target_doc, example_embedding):
        npz_path = join(self.shared_docs_path, "StateDocuments/", target_doc + "sudocu.npz")
        if npz_path in self._npz_cache:
            doc_bert_data = self._npz_cache[npz_path]
        else:
            doc_bert_data = np.load(npz_path, mmap_mode="r")['embedding']
            self._npz_cache[npz_path] = doc_bert_data
        state_start = self.doc_indicies[target_doc][0]
        rows = doc_bert_data[np.asarray([sid - state_start for sid in sentence_ids])]
        # Vectorized cosine similarity (1 - cosine distance, matching scipy's
        # cosine() exactly) against every candidate row at once, instead of a
        # Python-level loop calling scipy.spatial.distance.cosine() once per
        # row -- same anti-pattern (and same fix) as revision/filtering.py's
        # nearest_neighbor_bert_summary_filtering.
        row_norms = np.linalg.norm(rows, axis=1)
        ex_norm = np.linalg.norm(example_embedding)
        return (rows @ example_embedding) / (row_norms * ex_norm)

    # -- C-FREQ: TF-IDF --------------------------------------------------------
    def calculateNormalizedTFIDF(self, sentences_target, example_sentences):
        vec = TfidfVectorizer(analyzer='word', stop_words='english')
        vec.fit(example_sentences)
        scores = vec.transform(sentences_target).toarray().sum(axis=1)
        max_val = np.max(scores)
        if max_val > 0:
            scores = scores / max_val
        return scores.squeeze()

    # -- P-FREQ extension: Log Probability Ratio -------------------------------
    def calculateNormalizedLPR(self, sentences_target, example_sentences):
        vec = CountVectorizer(analyzer='word', stop_words='english')
        total = list(itertools.chain(sentences_target, example_sentences))
        vec.fit(total)
        ex_mat = vec.transform(example_sentences).toarray()
        tg_mat = vec.transform(sentences_target).toarray()
        ex_counts = np.sum(ex_mat, axis=0)
        tg_counts = np.sum(tg_mat, axis=0)
        ex_total = np.sum(ex_counts) or 1
        tg_total = np.sum(tg_counts) or 1
        ex_p = ex_counts / ex_total
        tg_p = tg_counts / tg_total

        out = []
        for row in tg_mat:
            nz = np.nonzero(row)[0]
            sc = 0.0
            for idx in nz:
                if tg_p[idx] != 0:
                    pr = ex_p[idx] / tg_p[idx]
                    if pr > 0:
                        lp = math.log10(pr)
                        if lp < 0:
                            sc += lp
            out.append(sc)
        out = minmax_scale(np.array(out)) - 1
        return out

    # -- TS: topic-distribution cosine similarity ------------------------------
    def topicScoresObjective(self, target_topic_scores, example_summaries, df):
        mean_sentences, _, _, _ = self.get_mean_stddev(example_summaries, df)
        # Vectorized cosine similarity against every candidate's topic vector
        # at once, instead of a Python-level loop calling scipy's cosine()
        # once per candidate -- same fix as calculateBSMeritScore above.
        mat = np.atleast_2d(np.transpose(target_topic_scores))
        row_norms = np.linalg.norm(mat, axis=1)
        mean_norm = np.linalg.norm(mean_sentences)
        return (mat @ mean_sentences) / (row_norms * mean_norm)

    def get_mean_stddev(self, example_summaires, df):
        topic_names = ['topic_' + str(i) for i in range(self.nTopics)]
        # sid -> row-index lookup + topic matrix built once per call, instead
        # of df[df["sid"] == sid] (a full linear scan of the whole corpus
        # DataFrame) once per example sentence -- O(n + k) instead of O(n*k)
        # for k example sentences.
        sid_to_row = {sid: i for i, sid in enumerate(df["sid"].to_numpy())}
        topic_matrix = df[topic_names].to_numpy()

        per_sentence, per_example = [], []
        for ex in example_summaires:
            ex_rows = []
            for sid in [int(s) for s in ex["sentence_ids"]]:
                row_idx = sid_to_row[sid]
                row = topic_matrix[row_idx:row_idx + 1]
                per_sentence.append(row)
                ex_rows.append(row)
            per_example.append(np.sum(np.array(ex_rows), axis=0))
        per_sentence = np.array(per_sentence)
        per_example = np.array(per_example)
        return (
            np.mean(per_sentence, axis=0).squeeze(),
            np.std(per_sentence, axis=0).squeeze(),
            np.mean(per_example, axis=0).squeeze(),
            np.std(per_example, axis=0).squeeze(),
        )

    def get_ex_embedding(self, example_summaires):
        emb = []
        for ex in example_summaires:
            doc = ex['state_name']
            npz_path = join(self.shared_docs_path, "StateDocuments/", doc + "sudocu.npz")
            if npz_path in self._npz_cache:
                data = self._npz_cache[npz_path]
            else:
                data = np.load(npz_path, mmap_mode="r")['embedding']
                self._npz_cache[npz_path] = data
            offset = self.doc_indicies[doc][0]
            for sid in [int(s) for s in ex["sentence_ids"]]:
                emb.append(data[sid - offset])
        return np.mean(np.array(emb), axis=0)

    def get_ex_sentences(self, example_summaires):
        out = None
        for ex in example_summaires:
            if out is None:
                out = list(ex['sentences'])
            else:
                out.extend([str(s) for s in ex['sentences']])
        return out

    # -- variant combiner ------------------------------------------------------
    def combine_scores(self, bs, tfidf, lpr, ts, mode="ALL"):
        """Combine per-sentence quality scores for a chosen variant.

        mode in VALID_OBJECTIVE_MODES. "ALL" reproduces Ex2Bundle's full objective.
        Individual modes reproduce Figure 12 ablation rows.
        """
        assert mode in VALID_OBJECTIVE_MODES, f"unknown mode: {mode}"
        if mode == "C-FREQ":
            return np.array(tfidf)
        if mode == "BS":
            return np.array(bs)
        if mode == "P-FREQ":
            return np.array(tfidf) + np.array(lpr)
        if mode == "TS":
            return np.array(ts)
        # ALL: original combined objective
        return np.array(bs) + np.array(tfidf) + np.array(lpr) + np.array(ts)