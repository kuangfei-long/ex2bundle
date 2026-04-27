"""
SuDocu baseline (Paper Section 5.1.3).

Original SuDocu demo system [11]: an LDA-topic-distribution-based ILP with a
*simple* fixed-step relaxation strategy. Distinct from Ex2Bundle in three ways:

  1. No SBERT pre-filter — the ILP is built over every sentence in the target
     document.
  2. Objective uses the precomputed `score` column from the CSV directly,
     rather than combining BS + TF-IDF + LPR + TS.
  3. Relaxation multiplier is `1/(k+1)` for the lower bound and `(k+1)` for
     the upper bound at iteration k — symmetric, fixed step, no exponential
     ramp.

This is what the paper compares against in Figure 9.
"""

import time

import numpy as np
import docplex.mp.model as cpx
import docplex.cp.parameters as params
from docplex.mp.conflict_refiner import ConflictRefiner

from models.base import SuDocuBase
from utils.filtering import Sentence_Prefilter_Wrapper
from utils.quality import Objective_Function_Wrapper


class SuDocuBaseline(SuDocuBase):
    """LDA-topic + simple fixed relaxation baseline."""

    def __init__(self, data_path, shared_docs_path, nTopics, num_examples,
                 is_generative=False, max_solvs=100, length_modifier=0.25):
        super().__init__(data_path, shared_docs_path, nTopics, num_examples, is_generative)

        cp = params.CpoParameters(LogVerbosity="Quiet", Presolve="On")
        cp.set_attribute("Presolve", "On")
        cp.set_attribute("LogVerbosity", "Quiet")

        self.max_solvs = max_solvs
        self.length_modifier = length_modifier
        self.filter_obj = Sentence_Prefilter_Wrapper(shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(shared_docs_path, nTopics)
        self.utilized_bounds = None

    def get_predicted_summary(self, target_doc, example_summaries, bounds=None):
        max_solv_count = self.max_solvs
        exceeded = False

        if bounds is None:
            bounds, avg_len = self.get_bounds(example_summaries)
        else:
            _, avg_len = self.get_bounds(example_summaries)
        bounds = np.array(bounds)
        assert len(bounds) == self.nTopics

        avg_len_step = self.length_modifier * avg_len
        target_df = self.df[self.df["name"] == target_doc]

        sentence_ids = target_df["sid"].to_numpy()
        topic_scores = target_df[self.topic_names].to_numpy().transpose()
        combined_score = target_df["score"].to_numpy()

        status = "none"
        solv_ctr = 0
        opt_model = None
        package_vars = None

        while status != "Optimal" and not exceeded:
            if solv_ctr < 1:
                opt_model = cpx.Model(name="SuDocu_Baseline_PaQL", log_output=False)
                package_vars = opt_model.integer_var_dict(sentence_ids, lb=0, ub=1, name="s")

                for j, topic in enumerate(topic_scores):
                    opt_model.add_constraint(
                        ct=opt_model.sum(topic[i] * package_vars[sid]
                                         for i, sid in enumerate(sentence_ids)) >= bounds[j][0],
                        ctname=f"constraint_min_topic{j}",
                    )
                    opt_model.add_constraint(
                        ct=opt_model.sum(topic[i] * package_vars[sid]
                                         for i, sid in enumerate(sentence_ids)) <= bounds[j][1],
                        ctname=f"constraint_max_topic{j}",
                    )
                opt_model.add_constraint(
                    ct=opt_model.sum(package_vars) >= -avg_len_step,
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
            else:
                # Simple fixed-step relaxation: multiply lb by 1/(k+1), ub by (k+1).
                for j in range(self.nTopics):
                    factor = 1.0 / (solv_ctr + 1)
                    new_lb = max(0.0, bounds[j][0] * factor)
                    new_ub = bounds[j][1] * (solv_ctr + 1)
                    opt_model.get_constraint_by_name(
                        f"constraint_min_topic{j}"
                    ).rhs = new_lb
                    opt_model.get_constraint_by_name(
                        f"constraint_max_topic{j}"
                    ).rhs = new_ub

            solu = opt_model.solve(log_output=False)
            solv_ctr += 1
            status = "Optimal" if solu is not None else "none"

            if solv_ctr > max_solv_count:
                exceeded = True

        self.utilized_bounds = bounds

        if exceeded or status != "Optimal":
            # Fall back to the first 10 sentences of the target document.
            fallback_ids = sentence_ids[:10].tolist()
            fallback_text = " ".join(
                str(target_df[target_df["sid"] == s]["sentence"].to_numpy()[0])
                for s in fallback_ids
            )
            return fallback_text, fallback_ids

        selected = []
        summary = []
        for var, val in solu.iter_var_values():
            if val > 0:
                idx = int(var.name[2:])
                selected.append(idx)
                summary.append(str(target_df[target_df["sid"] == idx]["sentence"].to_numpy()[0]))
        return " ".join(summary), selected
