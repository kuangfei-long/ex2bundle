"""
SubSumE experiment runner (used by Figure 9, Figure 12, ChatGPT comparison plots).

For each (intent, user-summary set) in SubSumE, splits into train/test, generates
predicted summaries with the supplied model, and records ROUGE-1/2/L, SBERT
semantic similarity, runtime, and per-topic score differences.

Saves results as .npz arrays under Results/<exp_folder>/<model_name>/.
"""

import json
import logging
import os
import random
import re
from os.path import join
from timeit import default_timer as timer
from multiprocessing.dummy import Pool

import numpy as np

from utils.evaluation import EvaluationScore
from utils.data_reader import UserDataReader

random.seed(7891)


def count_sentences(text):
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


class ExperimentRunner:
    def __init__(self, num_examples, num_test, users_path, data_path, nTopics,
                 min_range, max_index, shared_docs):
        self.num_examples = num_examples
        self.num_test = num_test
        self.users_path = users_path
        self.data_path = data_path
        self.nTopics = nTopics
        self.min_range = min_range
        self.max_range = max_index

        self.udr = UserDataReader(self.users_path, self.data_path, self.min_range, self.max_range)
        self.eval_scorer = EvaluationScore(shared_docs, data_path, nTopics)

        self.ground_truth, self.gt_indices = self.udr.read_summaries_list()
        self.intent_doc = np.array(self.udr.read_intent_doc())
        self.sudocu_data = np.array(self.udr.read_example_summaries_sudocu())
        self.intent_list = self.udr.read_intents()
        self.ex_range = list(range(num_examples + num_test))

    def evaluate_example(self, model, target_doc, gt_summary, gt_indices, example_summaries,
                         intent, output_file_path, ex_num, pool_num, trial_num, examples_processed):
        save_prob = random.uniform(0, 1)
        eval_start_time = timer()

        result = model.get_predicted_summary(target_doc, example_summaries)
        # Ex2Bundle returns 6-tuple (with timing/relax info); baselines return 2-tuple.
        if isinstance(result, tuple) and len(result) == 6:
            predicted_summary, _, _, _, _, _ = result
            summ_indices = []
        elif isinstance(result, tuple) and len(result) == 2:
            predicted_summary, summ_indices = result
        else:
            raise ValueError(f"Unexpected return: {type(result)}")
        eval_end_time = timer()

        scores = self.eval_scorer.compareScore(predicted_summary, gt_summary)
        summ_sim = self.eval_scorer.compare_summaries_sbert(predicted_summary, gt_summary)
        topic_score_diffs = []
        if (not model.is_generative) and summ_indices:
            topic_score_diffs = self.eval_scorer.compareTopicScores(summ_indices, gt_indices)

        ex_rouge_scores, ex_sbert_scores, ex_topic_diffs = [], [], []
        for ex_sum in example_summaries:
            ex_sentence_ids = [int(s) for s in ex_sum["sentence_ids"]]
            doc_name = ex_sum['state_name']
            ex_summary_txt = self.eval_scorer.get_example_summary_text(doc_name, ex_sentence_ids)
            ex_rouge_scores.append(self.eval_scorer.compareScore(predicted_summary, ex_summary_txt))
            ex_sbert_scores.append(self.eval_scorer.compare_summaries_sbert(predicted_summary, ex_summary_txt))
            if summ_indices:
                ex_topic_diffs.append(self.eval_scorer.compareTopicScores(summ_indices, ex_sentence_ids))

        if save_prob < 0.1:
            with open(join(output_file_path, "txts/",
                           f"ex_{ex_num}_pool_{pool_num}_trial_{trial_num}_summaries.txt"), "w") as f:
                f.write("Document:\n" + target_doc)
                f.write("\n\nIntent:\n" + intent)
                f.write("\n\nPredicted Summary:\n" + predicted_summary)
                f.write("\n\nGT:\n" + gt_summary)
                f.write("\n\nRouge-1, Rouge-2, Rouge-L: [p, r, f1, f2]:\n")
                for r in scores:
                    f.write(str(r) + "\n")
                f.write(f"\nSBERT sim. Score: {summ_sim}")
                f.write(f"\nTopic-Score Diffs: {topic_score_diffs}\n")

        return (scores, eval_end_time - eval_start_time, summ_sim, topic_score_diffs,
                ex_rouge_scores, ex_sbert_scores, ex_topic_diffs)

    def model_get_evaluation(self, model, trial_num, output_file_path, multi_processing=True):
        examples_processed = 0
        all_scores, all_runtimes, all_sbert, all_topic_diffs = [], [], [], []
        all_scores_wrt_ex, all_sbert_wrt_ex, all_topic_diffs_wrt_ex = [], [], []
        all_scores_by_intent = {intent: [] for intent in self.intent_list}

        for i, (intent, ground_truth, gt_indices, example_summaries) in enumerate(
            zip(self.intent_doc, self.ground_truth, self.gt_indices, self.sudocu_data)
        ):
            start_total = timer()
            if examples_processed % 10 == 0:
                logging.info("processed: %d examples", examples_processed)

            intent_text = list(intent.keys())[0]
            documents = np.array(list(intent.values())[0])

            train_split = random.sample(range(0, len(example_summaries)), self.num_examples)
            test_indices = [idx for idx in self.ex_range if idx not in train_split]

            example_set = example_summaries[train_split]
            test_docs = documents[np.array(test_indices)]
            test_gt = np.array(ground_truth)[np.array(test_indices)]
            test_gt_indices = np.array(gt_indices, dtype=object)[np.array(test_indices)]

            scores_pb, runtimes_pb, sbert_pb, topic_pb = [], [], [], []
            wrt_ex_scores_pb, wrt_ex_sbert_pb, wrt_ex_topic_pb = [], [], []

            pool_num = 0
            if multi_processing:
                args = [
                    (model, doc, gt, idx, example_set.tolist(), intent_text,
                     output_file_path, i, p, trial_num, examples_processed)
                    for p, (doc, gt, idx) in enumerate(zip(test_docs, test_gt, test_gt_indices))
                ]
                with Pool() as pool:
                    res = pool.starmap(self.evaluate_example, args)
                for r in res:
                    scores_pb.append(r[0]); runtimes_pb.append(r[1]); sbert_pb.append(r[2])
                    topic_pb.append(r[3]); wrt_ex_scores_pb.append(r[4])
                    wrt_ex_sbert_pb.append(r[5]); wrt_ex_topic_pb.append(r[6])
            else:
                for doc, gt, idx in zip(test_docs, test_gt, test_gt_indices):
                    s, rt, ss, td, exs, exsb, ext = self.evaluate_example(
                        model, doc, gt, idx, example_set.tolist(), intent_text,
                        output_file_path, i, pool_num, trial_num, examples_processed,
                    )
                    pool_num += 1
                    scores_pb.append(s); runtimes_pb.append(rt); sbert_pb.append(ss)
                    topic_pb.append(td); wrt_ex_scores_pb.append(exs)
                    wrt_ex_sbert_pb.append(exsb); wrt_ex_topic_pb.append(ext)

            scores_pb = np.array(scores_pb)
            runtimes_pb = np.array(runtimes_pb)
            assert scores_pb.shape[0] == self.num_test and scores_pb.shape[-1] == 4
            assert runtimes_pb.shape[0] == self.num_test

            if examples_processed % 10 == 0:
                logging.info("elapsed: %.4fs", timer() - start_total)
            examples_processed += 1

            all_scores_by_intent[intent_text].append(scores_pb.tolist())
            all_scores.append(scores_pb)
            all_runtimes.append(runtimes_pb)
            all_sbert.append(sbert_pb)
            all_topic_diffs.append(np.array(topic_pb))
            all_scores_wrt_ex.append(np.array(wrt_ex_scores_pb))
            all_sbert_wrt_ex.append(np.array(wrt_ex_sbert_pb))
            all_topic_diffs_wrt_ex.append(np.array(wrt_ex_topic_pb))

        return (
            np.array(all_scores).squeeze(),
            np.array(all_runtimes).squeeze(),
            all_scores_by_intent,
            np.array(all_sbert).squeeze(),
            np.array(all_topic_diffs).squeeze(),
            np.array(all_scores_wrt_ex).squeeze(),
            np.array(all_sbert_wrt_ex).squeeze(),
            np.array(all_topic_diffs_wrt_ex).squeeze(),
        )

    def get_model_analysis(self, model_cls, num_trials, trial_start, display_results,
                           model_name, shared_docs_path, exp_folder=None,
                           multi_processing=True, model_kwargs=None):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.makedirs(join(dir_path, "Results/"), exist_ok=True)
        out = join(dir_path, "Results/")
        if exp_folder:
            out = join(out, exp_folder)
            os.makedirs(out, exist_ok=True)
        out = join(out, model_name)
        os.makedirs(out, exist_ok=True)
        os.makedirs(join(out, "txts/"), exist_ok=True)
        logging.info("Running experiment, output -> %s", out)

        model_kwargs = model_kwargs or {}
        for i in range(trial_start, num_trials):
            model_inst = model_cls(
                self.data_path, shared_docs_path, self.nTopics,
                self.num_examples, is_generative=False, **model_kwargs,
            )
            ex_scores, ex_runtimes, intent_results, sbert_scores, ts_diffs, \
                wrt_scores, wrt_sbert, wrt_tsdiffs = self.model_get_evaluation(
                    model_inst, i, out, multi_processing
                )

            stem = lambda k: join(out, f"{k}_{self.min_range}_{self.max_range}_trail_{i}")
            np.savez(stem("all_scores_range"), scores=ex_scores)
            np.savez(stem("all_runtimes"), scores=ex_runtimes)
            np.savez(stem("all_sbert_scores"), scores=sbert_scores)
            np.savez(stem("all_ts_diffs"), scores=ts_diffs)
            np.savez(stem("all_scores_example"), scores=wrt_scores)
            np.savez(stem("all_sbert_example"), scores=wrt_sbert)
            np.savez(stem("all_ts_diffs_example"), scores=wrt_tsdiffs)
            with open(join(out, f"all_scores_range_by_intent_{self.min_range}_{self.max_range}_trail_{i}.txt"), 'w') as f:
                json.dump(intent_results, f)

            if display_results:
                logging.info("trial %d: avg ROUGE: %s", i, np.mean(ex_scores, axis=(0, 1)))
                logging.info("trial %d: avg SBERT: %.4f", i, np.mean(sbert_scores))
                logging.info("trial %d: avg runtime: %.4fs", i, np.mean(ex_runtimes))
