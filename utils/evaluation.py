"""
Evaluation metrics: ROUGE-1/2/L and SBERT-based semantic similarity.

`compareScore`  -> ROUGE p/r/f1/f2 for each of {rouge1, rouge2, rougeL}.
`compare_summaries_sbert` -> mean cosine sim between sentence-level SBERT embeddings.
`compareTopicScores` -> per-topic absolute difference in summed topic scores.
"""

import json
from os.path import join

import numpy as np
import pandas as pd
import torch
from rouge_score import rouge_scorer
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer
from nltk.tokenize import sent_tokenize


class EvaluationScore:
    def __init__(self, shared_docs_path, df_path, num_topics):
        self.shared_docs_path = shared_docs_path
        with open(join(self.shared_docs_path, "state_indices.txt")) as f:
            self.doc_indices = json.loads(f.read())
        self.nTopics = num_topics
        self.sen_transformer = SentenceTransformer('all-mpnet-base-v2')
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        with open(df_path) as f:
            sep = ';' if ';' in f.readline() else ','
        self.df = pd.read_csv(df_path, sep=sep)
        self.topic_names = np.array(['topic_' + str(i) for i in range(self.nTopics)])

    def compareScore(self, paql_summary, ground_truth):
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        scores = scorer.score(paql_summary, ground_truth)
        out = []
        for _, v in scores.items():
            parts = str(v).split(",")
            p = float(parts[0][16:])
            r = float(parts[1][8:])
            f1 = float(parts[2][10:-1])
            f2 = 0.0 if (p == 0 and r == 0) else (5.0 * p * r) / (4.0 * (p + r))
            out.append([p, r, f1, f2])
        return out

    def compareTopicScores(self, paql_summ_indicies, gt_summ_indicies):
        pred = self.df[self.df['sid'].isin(paql_summ_indicies)][self.topic_names].to_numpy().sum(axis=0)
        gt = self.df[self.df['sid'].isin(gt_summ_indicies)][self.topic_names].to_numpy().sum(axis=0)
        return np.absolute(gt - pred).tolist()

    def compareSummariesSBERTExamples(self, paql_summ_indicies, ex_summ_indicies, target_doc, example_doc):
        target_data = np.load(join(self.shared_docs_path, "StateDocuments/", target_doc.strip() + "sudocu.npz"))['embedding']
        target_offset = self.doc_indices[target_doc][0]
        pred_avg = np.mean(target_data[[i - target_offset for i in paql_summ_indicies]], axis=0)

        ex_data = np.load(join(self.shared_docs_path, "StateDocuments/", example_doc.strip() + "sudocu.npz"))['embedding']
        ex_offset = self.doc_indices[example_doc][0]
        gt_avg = np.mean(ex_data[[i - ex_offset for i in ex_summ_indicies]], axis=0)
        return 1 - cosine(pred_avg, gt_avg)

    def compare_summaries_sbert(self, pred_text, target_text):
        if not pred_text or not target_text:
            return 0.0
        pred_sents = sent_tokenize(str(pred_text))
        targ_sents = sent_tokenize(str(target_text))
        if not pred_sents or not targ_sents:
            return 0.0
        pred_emb = self.sen_transformer.encode(
            pred_sents, batch_size=len(pred_sents),
            convert_to_numpy=True, device=self.device, show_progress_bar=False,
        )
        targ_emb = self.sen_transformer.encode(
            targ_sents, batch_size=len(targ_sents),
            convert_to_numpy=True, device=self.device, show_progress_bar=False,
        )
        return float(1 - cosine(np.mean(pred_emb, axis=0), np.mean(targ_emb, axis=0)))

    def get_example_summary_text(self, state_name, ids):
        return " ".join(
            self.df[(self.df['name'] == state_name) & (self.df['sid'].isin(ids))]['sentence'].to_numpy()
        )
