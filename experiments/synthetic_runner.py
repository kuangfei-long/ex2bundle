"""
Synthetic-data experiment runner used by Figures 13 and 14.

Iterates over example-summary lengths k in {5, 10, 15, ..., 45} and over the
synthetic-data subfolders (one per topic), measuring per-document:
  - learning time (bound synthesis + ILP build)
  - ILP retrieval time
  - relaxation frequency
  - number of relaxed topics

Saves a single pkl with all per-(k, doc) measurements.
"""

import logging
import os
import pickle
import random
import re
import traceback

import numpy as np

from utils.data_reader import SyntheticUserDataReader

random.seed(7891)


def count_sentences(text):
    return len([s for s in re.split(r'[.!?]+', text) if s.strip()])


class SyntheticExperimentRunner:
    def __init__(self, num_examples, num_test, users_path, data_path, nTopics,
                 min_range, max_index, shared_docs, results_path,
                 states_file=None, sentence_lengths=range(5, 46, 5)):
        self.num_examples = num_examples
        self.num_test = num_test
        self.users_path = users_path
        self.data_path = data_path
        self.nTopics = nTopics
        self.min_range = min_range
        self.max_range = max_index
        self.shared_docs = shared_docs
        self.results_path = results_path
        self.sentence_lengths = list(sentence_lengths)
        self.states_file = states_file
        os.makedirs(results_path, exist_ok=True)

    def model_get_evaluation(self, model_cls, parent_synth_folder, num_test_docs=5):
        """Run scalability/relaxation scan. `parent_synth_folder` should contain
        per-topic subfolders, each holding `synthetic_data_<k>_sentences.json`.
        """
        states = []
        if self.states_file:
            with open(self.states_file, 'r') as f:
                for line in f:
                    states.append(line.strip())

        model_inst = model_cls(
            self.data_path, self.shared_docs, self.nTopics, self.num_examples,
            is_generative=False,
        )

        all_learning_pl, all_retrieval_pl = [], []
        all_avg_learning_pl, all_avg_retrieval_pl = [], []
        all_relax_freqs_pl, all_num_relax_pl = [], []
        all_avg_relax_freqs_pl = []
        predicted_summaries = []
        summary_length_retrieval_map = {}

        try:
            subfolders = [f.path for f in os.scandir(parent_synth_folder) if f.is_dir()]

            for k in self.sentence_lengths:
                logging.info("--- k = %d sentences ---", k)
                all_learn_pt, all_retr_pt = [], []
                avg_learn_pt, avg_retr_pt = [], []
                all_relax_pt, all_num_relax_pt = [], []
                avg_relax_pt = []

                for sub in subfolders:
                    upath = os.path.join(sub, f"synthetic_data_{k}_sentences.json")
                    if not os.path.exists(upath):
                        continue
                    udr = SyntheticUserDataReader(upath, self.data_path,
                                                  self.min_range, self.max_range)
                    train_split = random.sample(range(len(states) or 50), self.num_examples)
                    sudocu_data = np.array(udr.read_example_summaries_sudocu())
                    example_set = sudocu_data[train_split]

                    test_indices = [j for j in range(50) if j not in train_split]
                    test_docs = [states[j] for j in test_indices] if states else test_indices

                    learn_doc, retr_doc, relax_doc, nrelax_doc = [], [], [], []
                    for target in test_docs[:num_test_docs]:
                        try:
                            (pred, learn_t, ilp_t, slen, relax_freq,
                             num_relax) = model_inst.get_predicted_summary(target, example_set)
                            predicted_summaries.append(pred)
                            relax_doc.append(relax_freq)
                            nrelax_doc.append(num_relax)
                            retr_doc.append(ilp_t)
                            learn_doc.append(learn_t)
                            summary_length_retrieval_map.setdefault(slen, []).append(ilp_t)
                        except Exception as e:
                            logging.warning("Skipping %s (k=%d, %s): %s", target, k, sub, e)

                    if learn_doc:
                        avg_learn_pt.append(sum(learn_doc) / len(learn_doc))
                        avg_retr_pt.append(sum(retr_doc) / len(retr_doc))
                        avg_relax_pt.append(sum(relax_doc) / len(relax_doc))
                        all_relax_pt.extend(relax_doc)
                        all_num_relax_pt.extend(nrelax_doc)
                    all_learn_pt.extend(learn_doc)
                    all_retr_pt.extend(retr_doc)

                all_learning_pl.append(all_learn_pt)
                all_retrieval_pl.append(all_retr_pt)
                all_relax_freqs_pl.append(all_relax_pt)
                all_num_relax_pl.append(all_num_relax_pt)
                if avg_learn_pt:
                    all_avg_learning_pl.append(sum(avg_learn_pt) / len(avg_learn_pt))
                    all_avg_retrieval_pl.append(sum(avg_retr_pt) / len(avg_retr_pt))
                    all_avg_relax_freqs_pl.append(sum(avg_relax_pt) / len(avg_relax_pt))

        except Exception:
            logging.error("Experiment failed:\n%s", traceback.format_exc())

        finally:
            results = {
                "x_values": self.sentence_lengths,
                "summary_length_retrieval_map": summary_length_retrieval_map,
                # NB: original notebook had keys swapped here; preserved for
                # compatibility with `plot_figure14.py`.
                "all_avg_retrieval_times_per_sentence_len": all_avg_learning_pl,
                "all_avg_learning_times_per_sentence_len":  all_avg_retrieval_pl,
                "all_learning_times_per_sentence_len":      all_learning_pl,
                "all_retrieval_times_per_sentence_len":     all_retrieval_pl,
                "all_avg_relax_freqs_per_sentence_len":     all_avg_relax_freqs_pl,
                "all_relax_freqs_per_sentence_len":         all_relax_freqs_pl,
                "all_num_relaxed_topics_per_sentence_len":  all_num_relax_pl,
            }
            out_file = os.path.join(self.results_path, "evaluation_data.pkl")
            with open(out_file, "wb") as f:
                pickle.dump(results, f)
            logging.info("Saved results to %s", out_file)
