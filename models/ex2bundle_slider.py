"""
Slider-aware Ex2Bundle (Paper Section 4.1.3).

Supports two modes:

  - first_gen=True
      Standard bound relaxation, identical to ``Ex2Bundle`` but exposes
      ``slider_alg_vals`` so the caller can record stable bounds for later.

  - first_gen=False
      Slider relaxation: when the user moves a slider gamma to a new value,
      we may need to walk the slider back toward the last feasible (anchor)
      value to re-establish feasibility. Each step:
          gamma_tilde = gamma + r_m * sgn(gamma_anchor - gamma)
      and translate back to bounds via slider.calculate_bounds_from_slider.

This file mirrors the Flask-server implementation we shipped during the user
study (see paper Section 6) and is what the demo uses today.
"""

import time

import numpy as np
import docplex.mp.model as cpx
from docplex.mp.conflict_refiner import ConflictRefiner

from models.base import SuDocuBase
from utils.filtering import Sentence_Prefilter_Wrapper
from utils.quality import Objective_Function_Wrapper
from utils.slider import calculate_bounds_from_slider


class Ex2BundleSlider(SuDocuBase):
    def __init__(self, data_path, shared_docs_path, nTopics, num_examples=5,
                 is_generative=False, max_solvs=100, length_modifier=0.25):
        super().__init__(data_path, shared_docs_path, nTopics, num_examples, is_generative)
        self.max_solvs = max_solvs
        self.length_modifier = length_modifier
        self.filter_obj = Sentence_Prefilter_Wrapper(shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(shared_docs_path, nTopics)
        self.utilized_bounds = None
        self.slider_values = None

    def get_predicted_summary(
        self, user_id, target_doc, example_summaires, processed_ctr,
        bounds=None, first_gen=False, slider_alg_vals=None,
        alg_one_version=1, alg_two_version=1,
    ):
        max_solv_count = 1000 if first_gen else 100
        if (not first_gen) and slider_alg_vals is None:
            raise ValueError("slider_alg_vals required when first_gen=False")

        # 1. Bounds + candidate pool
        if bounds is None:
            bounds, avg_len = self.get_bounds(example_summaires)
        else:
            _, avg_len = self.get_bounds(example_summaires)
        bounds = np.array(bounds)

        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaires)
        ex_sentences = self.obj_func_obj.get_ex_sentences(example_summaires)
        avg_len_step = self.length_modifier * avg_len
        target_df = self.df[self.df['name'] == target_doc]
        step_sizes = target_df[self.topic_names].to_numpy().sum(axis=0) / (target_df.shape[0] / 2.0)

        slider_diffs = None
        relax_topics = None
        slider_vals = None
        if slider_alg_vals is not None:
            slider_diffs = slider_alg_vals["slider_val_diffs"]
            relax_topics = np.nonzero(slider_diffs)
            slider_vals = slider_alg_vals["slider_vals"]
        else:
            relax_topics = np.zeros((self.nTopics))

        size_mult = 7.5
        filtered_ids = self.filter_obj.nearest_neighbor_bert_summary_filtering(
            avg_ex_embedding=ex_embedding, test_doc=target_doc, top_k=int(avg_len * size_mult),
        )
        sub_df = self.df[(self.df['name'] == target_doc) & (self.df['sid'].isin(filtered_ids))]
        sentence_ids = sub_df['sid'].to_numpy()
        topic_scores = sub_df[self.topic_names].to_numpy().transpose()
        sentences_target = sub_df['sentence'].to_numpy()

        # 2. Combined objective (uses ALL components in deployed version)
        bs = self.obj_func_obj.calculateBSMeritScore(sentence_ids, target_doc, ex_embedding)
        clean_target = self.obj_func_obj.cleanSentences(sentences_target)
        clean_examples = self.obj_func_obj.cleanSentences(ex_sentences)
        tfidf = self.obj_func_obj.calculateNormalizedTFIDF(clean_target, clean_examples)
        lpr = self.obj_func_obj.calculateNormalizedLPR(clean_target, clean_examples)
        combined_score = np.array(bs) + np.array(tfidf) + np.array(lpr)

        # 3. Iteratively solve
        status = "none"
        solv_ctr = 0
        exceeded = False

        while status != 'Optimal' and not exceeded:
            step_ctr = max(int(solv_ctr / 10.0), 1)
            step_mult = max(int(np.exp(step_ctr * 0.5)), 1)

            opt_model = cpx.Model(name="Ex2Bundle_PaQL_Slider")
            package_vars = opt_model.integer_var_dict(sentence_ids, lb=0, ub=1, name="s")

            if first_gen:
                if alg_one_version == 1:
                    self._cplex_relax_alg_one(
                        opt_model, package_vars, bounds, topic_scores, sentence_ids,
                        step_sizes, relax_topics, solv_ctr, step_mult,
                    )
                else:
                    self._smallest_range_alg_one(
                        opt_model, package_vars, bounds, topic_scores, sentence_ids,
                        step_sizes, solv_ctr, step_mult,
                    )

            if solv_ctr > max_solv_count:
                exceeded = True
                bounds = slider_alg_vals['stable_bounds']
                for j, topic in enumerate(topic_scores):
                    for i, sid in enumerate(sentence_ids):
                        opt_model.add_constraint(
                            ct=opt_model.sum(topic[i] * package_vars[sid]) >= bounds[j][0],
                            ctname="constraint_min_topic{0}".format(j),
                        )
                        opt_model.add_constraint(
                            ct=opt_model.sum(topic[i] * package_vars[sid]) <= bounds[j][1],
                            ctname="constraint_max_topic{0}".format(j),
                        )
            elif (not first_gen) and slider_alg_vals is not None:
                if alg_two_version == 1:
                    self._cplex_relax_alg_two(
                        opt_model, package_vars, bounds, topic_scores, sentence_ids,
                        slider_vals, slider_diffs, slider_alg_vals,
                        relax_topics, solv_ctr, step_mult,
                    )
                else:
                    self._largest_diff_alg_two(
                        opt_model, package_vars, bounds, topic_scores, sentence_ids,
                        slider_vals, slider_diffs, slider_alg_vals, solv_ctr, step_mult,
                    )

            opt_model.add_constraint(
                ct=opt_model.sum(package_vars) >= avg_len - avg_len_step,
                ctname="constraint_min_len",
            )
            opt_model.add_constraint(
                ct=opt_model.sum(package_vars) <= avg_len + avg_len_step,
                ctname="constraint_max_len",
            )

            objective = opt_model.sum(
                combined_score[i] * package_vars[sid] for i, sid in enumerate(sentence_ids)
            )
            opt_model.maximize(objective)

            solu = opt_model.solve(log_output=False)
            solv_ctr += 1
            status = "Optimal" if solu is not None else "none"

            if status == "none":
                cr = ConflictRefiner()
                cr_res = cr.refine_conflict(opt_model, display=False)
                relax = set()
                for conflict in cr_res.iter_conflicts():
                    name = str(conflict[0])
                    if "topic" in name:
                        try:
                            relax.add(int(name.replace("constraint_min_topic", "")
                                              .replace("constraint_max_topic", "")))
                        except ValueError:
                            pass
                relax_topics = list(relax)

        if exceeded:
            return ("def_sum --------------- error state", [])

        self.utilized_bounds = bounds
        self.slider_values = slider_vals

        selected = [v.name for v, val in solu.iter_var_values() if val > 0]
        summary_indices, summary = [], []
        for s in selected:
            sid = int(s[2:])
            summary_indices.append(sid)
            summary.append(str(sub_df[sub_df['sid'] == sid]['sentence'].to_numpy()[0]))
        return (" ".join(summary), summary_indices)

    # -- Algorithm 1 (initial relaxation, no sliders) --------------------------
    def _cplex_relax_alg_one(self, model, package_vars, bounds, topic_scores,
                             sentence_ids, step_sizes, relax_topics, solv_ctr, step_mult):
        for j, topic in enumerate(topic_scores):
            if (j in np.array(relax_topics)) and solv_ctr > 0:
                lb_new = bounds[j][0] - step_mult * step_sizes[j]
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
                bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0],
                    ctname="constraint_min_topic{0}".format(j),
                )
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1],
                    ctname="constraint_max_topic{0}".format(j),
                )

    def _smallest_range_alg_one(self, model, package_vars, bounds, topic_scores,
                                sentence_ids, step_sizes, solv_ctr, step_mult):
        smallest = np.argmin(np.abs(bounds[:, 1] - bounds[:, 0]))
        for j, topic in enumerate(topic_scores):
            if (j == smallest) and solv_ctr > 0:
                lb_new = bounds[j][0] - step_mult * step_sizes[j]
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
                bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0],
                    ctname="constraint_min_topic{0}".format(j),
                )
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1],
                    ctname="constraint_max_topic{0}".format(j),
                )

    # -- Algorithm 2 (slider-aware relaxation) ---------------------------------
    def _cplex_relax_alg_two(self, model, package_vars, bounds, topic_scores,
                             sentence_ids, slider_vals, slider_diffs, slider_alg_vals,
                             relax_topics, solv_ctr, step_mult):
        """Walk slider gamma toward feasible anchor, then re-derive bounds."""
        for j, topic in enumerate(topic_scores):
            if (j in np.array(relax_topics)) and solv_ctr > 0:
                if step_mult > abs(slider_vals[j]):
                    slider_vals[j] = 0
                else:
                    slider_vals[j] = slider_vals[j] + step_mult * np.sign(slider_diffs[j])
                bounds[j] = calculate_bounds_from_slider(j, slider_vals[j], slider_alg_vals)

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0],
                    ctname="constraint_min_topic{0}".format(j),
                )
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1],
                    ctname="constraint_max_topic{0}".format(j),
                )

    def _largest_diff_alg_two(self, model, package_vars, bounds, topic_scores,
                              sentence_ids, slider_vals, slider_diffs, slider_alg_vals,
                              solv_ctr, step_mult):
        largest = np.argmax(np.abs(slider_diffs))
        for j, topic in enumerate(topic_scores):
            if (j == largest) and solv_ctr > 0:
                slider_vals[j] = slider_vals[j] + step_mult * np.sign(slider_diffs[j])
                bounds[j] = calculate_bounds_from_slider(j, slider_vals[j], slider_alg_vals)
                slider_diffs[j] = slider_alg_vals['prev_slider_vals'][j] - slider_vals[j]

            for i, sid in enumerate(sentence_ids):
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) >= bounds[j][0],
                    ctname="constraint_min_topic{0}".format(j),
                )
                model.add_constraint(
                    ct=model.sum(topic[i] * package_vars[sid]) <= bounds[j][1],
                    ctname="constraint_max_topic{0}".format(j),
                )

    def get_utilized_bounds(self):
        return self.utilized_bounds.tolist() if self.utilized_bounds is not None else []

    def get_utilized_slider_values(self):
        return np.array(self.slider_values).tolist() if self.slider_values is not None else []
