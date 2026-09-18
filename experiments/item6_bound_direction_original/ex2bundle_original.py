"""
Restored, unmodified copy of models/ex2bundle.py as of commit 1f9c0cd (the
original Item-6 "Add bound-direction relaxation experiments" commit), before
the Section-4.5 Sketch-Refine refactor (ef7f2c9) dropped relaxation_mode/
bound_pad support from the shared models/ex2bundle.py. Kept local to this
experiment folder so the three relaxation strategies are available natively
(relaxation_mode=, bound_pad=, self.last_objective, etc.) without touching
the shared models/ex2bundle.py, which other experiments still depend on.

Ex2Bundle model: end-to-end intent-aware bundle retrieval (Paper Section 4).

Pipeline per call (`get_predicted_summary`):
  1. Synthesize intent bounds from example summaries.                  (4.1.1)
  2. Build the package-query ILP with topic + length constraints.       (4.3)
  3. If infeasible, identify violated constraints and relax them.       (4.1.2)
     - Primary: CPLEX ConflictRefiner (preferred, paper's main method).
     - Fallback: simple range heuristic (constraints with below-avg width).
  4. Iterate with exponential step multiplier r_m until feasible.
  5. Return the selected sentences (the bundle B).

The objective function is parameterized via `objective_mode` to support the
Figure 12 quality-function variants (C-FREQ, BS, P-FREQ, TS, ALL).

Returns: (summary_text, learning_time, ilp_solve_time,
          summary_length, relax_freq, num_relaxed_topics)
The 6-tuple is consumed by experiments/synthetic_runner.py for Figs. 13-14.
"""

import time

import numpy as np
import docplex.mp.model as cpx
import docplex.cp.parameters as params
from docplex.mp.conflict_refiner import ConflictRefiner
from docplex.mp.relaxer import Relaxer

# Supported bound-relaxation strategies (Revision Item 6, "bound direction").
#   symmetric   -- current algorithm: widen BOTH sides of every violated topic.
#   directional -- IIS identifies the violated side; widen only that side.
#   feasopt     -- one-shot CPLEX FeasOpt (Relaxer): minimal total relaxation.
VALID_RELAXATION_MODES = ("symmetric", "directional", "feasopt")

from models.base import SuDocuBase
from utils.filtering import Sentence_Prefilter_Wrapper
from utils.quality import Objective_Function_Wrapper, VALID_OBJECTIVE_MODES


class Ex2Bundle(SuDocuBase):
    """Ex2Bundle: bound-relaxed package-query retrieval."""

    def __init__(self, data_path, shared_docs_path, nTopics, num_examples, is_generative,
                 max_solvs=50, length_modifier=0.25, objective_mode="ALL",
                 use_conflict_refiner=True, relaxation_mode="symmetric", bound_pad=0.1):
        super().__init__(data_path, shared_docs_path, nTopics, num_examples, is_generative)

        # Quiet CPLEX presolve
        myparams = params.CpoParameters(LogVerbosity='Quiet', Presolve='On')
        myparams.set_attribute('Presolve', 'On')
        myparams.set_attribute('LogVerbosity', 'Quiet')

        self.max_solvs = max_solvs
        self.length_modifier = length_modifier
        assert objective_mode in VALID_OBJECTIVE_MODES, (
            f"objective_mode must be one of {VALID_OBJECTIVE_MODES}; got {objective_mode}"
        )
        self.objective_mode = objective_mode
        self.use_conflict_refiner = use_conflict_refiner
        assert relaxation_mode in VALID_RELAXATION_MODES, (
            f"relaxation_mode must be one of {VALID_RELAXATION_MODES}; got {relaxation_mode}"
        )
        self.relaxation_mode = relaxation_mode
        self.bound_pad = bound_pad

        self.filter_obj = Sentence_Prefilter_Wrapper(shared_docs_path, nTopics)
        self.obj_func_obj = Objective_Function_Wrapper(shared_docs_path, nTopics)

        self.utilized_bounds = None
        self.slider_values = None

        # Item-6 instrumentation, refreshed on every get_predicted_summary call.
        # (Exposed on the instance because the 6-tuple return contract is shared
        #  with the Fig 13/14 and RQ2 runners and must stay stable.)
        self.initial_bounds = None       # bounds right after synthesis, pre-relaxation
        self.last_relax_freq = 0         # number of relaxation rounds (feasopt: 1)
        self.last_num_relaxed = 0        # number of distinct topics relaxed
        self.last_relax_magnitude = 0.0  # sum |relaxed_rhs - initial_rhs| over topics
        self.last_objective = None       # final ILP objective (merit score) of the returned bundle
        self.last_selected_ids = []      # sentence ids in the returned bundle

    def get_predicted_summary(self, target_doc, example_summaries, bounds=None):
        max_solv_count = 50
        exceeded = False
        start_learn = time.time()

        # 1. Bound synthesis (or accept user-supplied bounds)
        if bounds is None:
            bounds, avg_len = self.get_bounds(example_summaries, bound_pad=self.bound_pad)
            bounds = np.array(bounds)
        else:
            avg_len = self.get_avg_summaries_length(example_summaries)
            bounds = np.array(bounds)
        assert len(bounds) == self.nTopics
        bounds = bounds.astype(float)
        self.initial_bounds = bounds.copy()

        # 2. Build candidate pool via SBERT prefiltering
        ex_embedding = self.obj_func_obj.get_ex_embedding(example_summaries)
        ex_sentences = self.obj_func_obj.get_ex_sentences(example_summaries)
        avg_len_step = self.length_modifier * avg_len

        target_df = self.df[self.df['name'] == target_doc]
        target_doc_scores = target_df[self.topic_names].to_numpy().sum(axis=0)
        # Step-size epsilon_j = F_j(B) / (|T_q| * delta), delta = 0.5 (paper Section 4.1.2).
        step_sizes = target_doc_scores / (target_df.shape[0] / 2.0)
        relax_topics = []
        relax_freq = 0

        size_mult = 10
        pool_size = min(int(avg_len * size_mult), 100)
        filtered_ids = self.filter_obj.nearest_neighbor_bert_summary_filtering(
            avg_ex_embedding=ex_embedding, test_doc=target_doc, top_k=pool_size,
        )
        sub_df = target_df[target_df['sid'].isin(filtered_ids)]
        sentence_ids = sub_df['sid'].to_numpy()
        topic_scores = sub_df[self.topic_names].to_numpy().transpose()
        sentences_target = sub_df['sentence'].to_numpy()

        # 3. Quality-function components (Paper Section 4.2)
        bs = self.obj_func_obj.calculateBSMeritScore(sentence_ids, target_doc, ex_embedding)
        clean_target = self.obj_func_obj.cleanSentences(sentences_target)
        clean_examples = self.obj_func_obj.cleanSentences(ex_sentences)
        tfidf = self.obj_func_obj.calculateNormalizedTFIDF(clean_target, clean_examples)
        lpr = self.obj_func_obj.calculateNormalizedLPR(clean_target, clean_examples)
        ts = self.obj_func_obj.topicScoresObjective(topic_scores, example_summaries, self.df)
        combined_score = self.obj_func_obj.combine_scores(
            bs, tfidf, lpr, ts, mode=self.objective_mode
        )

        # 4. Build & solve the ILP under the selected relaxation strategy.
        status = "none"
        solv_ctr = 0
        opt_model = None
        package_vars = None
        learning_time = 0.0
        ilp_solve_time = 0.0
        relax_directional = []  # list of (topic_idx, "min"|"max") for directional mode

        if self.relaxation_mode == "feasopt":
            # One-shot CPLEX FeasOpt: build once, and if infeasible let the
            # Relaxer find the minimal total bound relaxation (Item 6).
            opt_model, package_vars = self._build_base_model(
                sentence_ids, topic_scores, bounds, combined_score, avg_len, avg_len_step
            )
            learning_time = time.time() - start_learn
            ilp_start = time.time()
            opt_model.parameters.timelimit.set(60)
            solu = opt_model.solve(log_output=False)
            if solu is None:
                solu, bounds, relax_freq, relax_topics = self._feasopt_relax(opt_model, bounds)
            ilp_solve_time = time.time() - ilp_start
            exceeded = solu is None
        else:
            while status != 'Optimal' and not exceeded:
                # Exponential step multiplier r_m (Section 4.1.2).
                step_ctr = max(int(solv_ctr / 10.0), 1)
                step_mult = max(int(np.exp(step_ctr * 0.5)), 1)

                if solv_ctr < 1:
                    opt_model, package_vars = self._build_base_model(
                        sentence_ids, topic_scores, bounds, combined_score, avg_len, avg_len_step
                    )
                elif self.relaxation_mode == "directional":
                    self._relax_directional(
                        opt_model, bounds, step_sizes, relax_directional, solv_ctr, step_mult
                    )
                else:  # symmetric (current algorithm)
                    self._relax_violated_bounds(
                        opt_model, bounds, step_sizes, relax_topics, solv_ctr, step_mult
                    )

                learning_time = time.time() - start_learn
                ilp_start = time.time()
                opt_model.parameters.timelimit.set(60)
                solu = opt_model.solve(log_output=False)
                ilp_solve_time = time.time() - ilp_start

                solv_ctr += 1
                status = "Optimal" if solu is not None else "none"

                if status == "none":
                    if self.relaxation_mode == "directional":
                        relax_directional, relax_topics, round_relaxed = \
                            self._identify_violated_directional(opt_model, bounds)
                    else:
                        relax_topics, round_relaxed = self._identify_violated_constraints(
                            opt_model, bounds
                        )
                    if round_relaxed:
                        relax_freq += 1

                if solv_ctr > max_solv_count:
                    exceeded = True

        self.utilized_bounds = np.array(bounds, dtype=float)
        self.last_relax_freq = relax_freq
        self.last_num_relaxed = (
            0 if (isinstance(relax_topics, np.ndarray) and np.all(relax_topics == 0))
            else len(relax_topics)
        )
        self.last_relax_magnitude = float(
            np.sum(np.abs(self.utilized_bounds - self.initial_bounds))
        )

        if exceeded:
            self.last_objective = None
            self.last_selected_ids = []
            return ("def_sum --------------- error state", learning_time, ilp_solve_time, 0,
                    relax_freq, len(relax_topics))

        # 5. Extract bundle
        selected_ids = [v.name for v, val in solu.iter_var_values() if val > 0]
        summary_indices, summary = [], []
        for sid_str in selected_ids:
            sid = int(sid_str[2:])
            summary_indices.append(sid)
            summary.append(str(sub_df[sub_df['sid'] == sid]['sentence'].to_numpy()[0]))

        # Item-6 (Matteo): record the returned bundle and its merit objective so
        # we can check whether solutions/objectives differ across strategies even
        # when the relaxed bounds differ substantially.
        try:
            self.last_objective = float(solu.objective_value)
        except Exception:
            self.last_objective = None
        self.last_selected_ids = sorted(summary_indices)

        return (
            " ".join(summary),
            learning_time,
            ilp_solve_time,
            len(summary_indices),
            relax_freq,
            0 if (isinstance(relax_topics, np.ndarray) and np.all(relax_topics == 0)) else len(relax_topics),
        )

    # -- ILP construction ------------------------------------------------------

    def _build_base_model(self, sentence_ids, topic_scores, bounds,
                          combined_score, avg_len, avg_len_step):
        """Build the initial package-query ILP (topic + length constraints)."""
        opt_model = cpx.Model(name="Ex2Bundle_PaQL", log_output=False, cts_by_name=True)
        package_vars = opt_model.integer_var_dict(sentence_ids, lb=0, ub=1, name="s")

        for j, topic in enumerate(topic_scores):
            opt_model.add_constraint(
                ct=opt_model.sum(topic[i] * package_vars[sid]
                                 for i, sid in enumerate(sentence_ids)) >= bounds[j][0],
                ctname="constraint_min_topic{0}".format(j),
            )
            opt_model.add_constraint(
                ct=opt_model.sum(topic[i] * package_vars[sid]
                                 for i, sid in enumerate(sentence_ids)) <= bounds[j][1],
                ctname="constraint_max_topic{0}".format(j),
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
        return opt_model, package_vars

    @staticmethod
    def _parse_topic_constraint(name):
        """('min'|'max', j) for a topic-constraint name, else None.

        Accepts either a bare ctname ('constraint_min_topic3', from
        ConflictRefiner) or a full 'name: expr' string (from Relaxer).
        """
        key = str(name).split(":")[0].strip()
        for side, prefix in (("min", "constraint_min_topic"), ("max", "constraint_max_topic")):
            if key.startswith(prefix):
                try:
                    return side, int(key[len(prefix):])
                except ValueError:
                    return None
        return None

    # -- Bound relaxation (Paper Section 4.1.2) --------------------------------

    def _identify_violated_constraints(self, opt_model, bounds):
        """Return (set_of_topic_indices_to_relax, did_anything_get_added).

        Tries CPLEX ConflictRefiner first (paper's primary method); falls back
        to the simple "below-average-width" range heuristic.
        """
        relax = set()
        round_relaxed = False

        if self.use_conflict_refiner:
            try:
                cr = ConflictRefiner()
                cr_res = cr.refine_conflict(opt_model, display=False)
                for conflict in cr_res.iter_conflicts():
                    name = str(conflict[0])
                    if "topic" in name:
                        # constraint name "constraint_min_topic{j}" or "constraint_max_topic{j}"
                        try:
                            relax.add(int(name.replace("constraint_min_topic", "")
                                              .replace("constraint_max_topic", "")))
                            round_relaxed = True
                        except ValueError:
                            pass
            except Exception:
                # CPLEX ConflictRefiner can fail on some problem shapes; fall through.
                pass

        if not relax:
            # Range heuristic fallback.
            bound_diffs = np.abs(np.array(bounds)[:, 1:2] - np.array(bounds)[:, 0:1]).squeeze()
            avg_diff = np.mean(bound_diffs)
            for i in range(self.nTopics):
                if np.abs(bound_diffs[i]) < avg_diff:
                    relax.add(i)
                    round_relaxed = True

        return list(relax), round_relaxed

    def _relax_violated_bounds(self, model, bounds, step_sizes, relax_topics, solv_ctr, step_mult):
        """Symmetrically widen the bounds of every violated constraint.

        Lower bound is clipped at 0 (feature score is a SUM, can't go negative).
        Upper bound has no theoretical cap.
        """
        for j in range(self.nTopics):
            if (j in np.array(relax_topics)) and solv_ctr > 0:
                lb_new = bounds[j][0] - step_mult * step_sizes[j]
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
                bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]

            model.get_constraint_by_name("constraint_min_topic{0}".format(j)).rhs = bounds[j][0]
            model.get_constraint_by_name("constraint_max_topic{0}".format(j)).rhs = bounds[j][1]

    # -- Directional relaxation (Item 6: IIS + directional) --------------------

    def _identify_violated_directional(self, opt_model, bounds):
        """Like _identify_violated_constraints, but keeps the violated SIDE.

        Returns (directional_pairs, topic_indices, round_relaxed) where
        directional_pairs is a list of (topic_idx, 'min'|'max').
        """
        directional = []
        topics = set()
        round_relaxed = False

        if self.use_conflict_refiner:
            try:
                cr = ConflictRefiner()
                cr_res = cr.refine_conflict(opt_model, display=False)
                for conflict in cr_res.iter_conflicts():
                    parsed = self._parse_topic_constraint(conflict[0])
                    if parsed is None:
                        continue
                    side, j = parsed
                    directional.append((j, side))
                    topics.add(j)
                    round_relaxed = True
            except Exception:
                pass

        if not directional:
            # Fallback: no direction available, widen both sides of the
            # below-average-width topics (degenerates to symmetric).
            bound_diffs = np.abs(np.array(bounds)[:, 1:2] - np.array(bounds)[:, 0:1]).squeeze()
            avg_diff = np.mean(bound_diffs)
            for i in range(self.nTopics):
                if np.abs(bound_diffs[i]) < avg_diff:
                    directional.extend([(i, "min"), (i, "max")])
                    topics.add(i)
                    round_relaxed = True

        return directional, list(topics), round_relaxed

    def _relax_directional(self, model, bounds, step_sizes, relax_directional, solv_ctr, step_mult):
        """Widen ONLY the violated side of each flagged constraint.

        Contrast with _relax_violated_bounds, which widens both sides.
        """
        for (j, side) in relax_directional:
            if solv_ctr <= 0:
                continue
            if side == "min":
                lb_new = bounds[j][0] - step_mult * step_sizes[j]
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
            else:  # "max"
                bounds[j][1] = bounds[j][1] + step_mult * step_sizes[j]

        for j in range(self.nTopics):
            model.get_constraint_by_name("constraint_min_topic{0}".format(j)).rhs = bounds[j][0]
            model.get_constraint_by_name("constraint_max_topic{0}".format(j)).rhs = bounds[j][1]

    # -- FeasOpt relaxation (Item 6: CPLEX Relaxer) ----------------------------

    def _feasopt_relax(self, opt_model, bounds):
        """One-shot CPLEX FeasOpt: minimal total relaxation to feasibility.

        Reads each topic constraint's relaxation amount back into `bounds`
        (min constraints move down, max constraints move up).
        Returns (solution, relaxed_bounds, relax_freq, relaxed_topic_indices).
        """
        bounds = np.array(bounds, dtype=float)
        try:
            relaxer = Relaxer()
            solu = relaxer.relax(opt_model)
        except Exception:
            return None, bounds, 0, []
        if solu is None:
            return None, bounds, 0, []

        # CPLEX reports the relaxation as a SIGNED delta to add to the RHS
        # (negative when loosening a >= min bound, positive for a <= max bound).
        relaxed_topics = set()
        for ct, amount in relaxer.iter_relaxations():
            if amount == 0:
                continue
            parsed = self._parse_topic_constraint(getattr(ct, "name", None) or ct)
            if parsed is None:
                continue
            side, j = parsed
            if side == "min":
                lb_new = bounds[j][0] + amount
                bounds[j][0] = lb_new if lb_new > 0 else 0.0
            else:  # "max"
                bounds[j][1] = bounds[j][1] + amount
            relaxed_topics.add(j)

        # relax_freq = 1 relaxation "round" if anything was relaxed.
        relax_freq = 1 if relaxed_topics else 0
        return solu, bounds, relax_freq, list(relaxed_topics)
