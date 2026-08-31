"""
SketchRefine query evaluation (paper Section 4), ported from the algorithm in
matteo-brucato/Scalable-PaQL-Queries (quad_tree.py, sketch_refine.py,
greedy_backtracking.py, cplex_interface.py) into this project's in-memory
pandas/docplex setting, in place of that repo's Postgres-backed persisted
clustering.

Used by models/ex2bundle.py's Ex2Bundle via do_sketch_refine=True, in place of
one big DIRECT ILP over the whole SBERT-prefiltered candidate pool.

Three steps (paper Figure 2):
  1. PARTITION (_KDTreePartition). Split the candidate pool into groups no
     larger than size_threshold (Definition 1, tau), one dimension at a time
     (a k-d tree, not quad_tree.py's 2^k-way split -- see class docstring).
  2. SKETCH (SketchRefineSolver.solve, stage 1). Solve once over each group's
     representative (centroid row), bounded by group size.
  3. REFINE (stage 2 / _backtrack). Greedy backtracking replaces each
     representative with real tuples, one group at a time, fixing other
     groups' contributions as constant offsets (paper Section 4.2.2).

Ported the algorithm, not the code: the whole candidate pool fits in memory
here (no persisted clustering reused across queries), so SKETCH always solves
every group at once and REFINE never starts from an "empty" group.

REPEAT K (max_repeat): lets a sentence be selected more than once, needed
when the candidate pool is smaller than the requested package length.
"""

import time
from collections import deque

import numpy as np
import docplex.mp.model as cpx


class SketchRefineInfeasible(Exception):
    """SKETCH was infeasible, or REFINE's backtracking search was exhausted.
    Per paper Section 4.4 this may be false infeasibility (low, bounded
    probability), not a bug."""


class _RefineTimeout(Exception):
    """Internal: REFINE's wall-clock budget ran out mid-search."""


class _KDTreePartition:
    """k-d-tree partitioning (paper Section 4.1's PARTITION step), adapted
    from Scalable-PaQL-Queries's quad_tree.py.

    quad_tree.py splits all k attributes at once (2^k-way per split), which
    over-fragments on this project's 10-dimensional data -- empirically, the
    first split alone explodes into hundreds of near-singleton groups
    regardless of size_threshold. This class splits one dimension at a time
    instead (a real k-d tree), so groups shrink gradually as size_threshold
    is lowered.

    Split dimension: whichever attribute has the largest spread among a
    group's members. Pivot: that dimension's mean, ties broken randomly.
    Stops when every group meets size_threshold (and radius_limit, if given)
    or MAX_CLUST_DEPTH rounds have passed.
    """

    MAX_CLUST_DEPTH = 64

    def __init__(self, clust_attrs, size_threshold, radius_limit=None, rng=None):
        self.clust_attrs = np.asarray(clust_attrs, dtype=float)
        self.n, self.k = self.clust_attrs.shape
        self.size_threshold = max(1, int(size_threshold))
        self.radius_limit = radius_limit
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.groups = self._fit()

    def _violates(self, members):
        if len(members) > self.size_threshold:
            return True
        if self.radius_limit is not None and len(members) > 1:
            centroid = self.clust_attrs[members].mean(axis=0)
            radius = np.abs(self.clust_attrs[members] - centroid).max()
            if radius > self.radius_limit:
                return True
        return False

    def _split_dim(self, members):
        vals = self.clust_attrs[members]
        spans = vals.max(axis=0) - vals.min(axis=0)
        return int(np.argmax(spans))

    def _fit(self):
        groups = {0: list(range(self.n))}
        depth = 0
        while True:
            next_groups = {}
            next_gid = 0
            changed = False
            for members in groups.values():
                if not self._violates(members):
                    next_groups[next_gid] = members
                    next_gid += 1
                    continue
                changed = True
                d = self._split_dim(members)
                pivot = self.clust_attrs[members, d].mean()
                lo, hi = [], []
                for i in members:
                    v = self.clust_attrs[i, d]
                    if v == pivot:
                        (lo if self.rng.integers(0, 2) == 0 else hi).append(i)
                    elif v < pivot:
                        lo.append(i)
                    else:
                        hi.append(i)
                for sub_members in (lo, hi):
                    if sub_members:
                        next_groups[next_gid] = sub_members
                        next_gid += 1
            groups = next_groups
            depth += 1
            if not changed or depth > self.MAX_CLUST_DEPTH:
                break
        return groups


class SketchRefineSolver:
    """SKETCH + REFINE query evaluation (paper Section 4.2) over an in-memory
    candidate pool.
    """

    def __init__(self, sentence_ids, topic_scores, combined_score, cplex_threads,
                 size_threshold, timelimit=60, radius_limit=None, rng_seed=0, max_repeat=1,
                 refine_timelimit=None):
        """
        sentence_ids : array-like, shape (n,). Candidate pool's sids.
        topic_scores : array-like, shape (nTopics, n). Column i matches
            sentence_ids[i].
        combined_score : array-like, shape (n,). Per-sentence objective
            coefficient (Section 4.2's quality function, already combined).
        size_threshold : int. Paper's tau -- max tuples per group.
        radius_limit : float or None. Paper's omega. None (default) partitions
            on size alone -- cheaper, forgoes the formal approximation bound.
        max_repeat : int >= 1. REPEAT K + 1; bounds how many times one
            sentence may appear in the package. Needed when the candidate
            pool is smaller than the requested package length.
        refine_timelimit : float or None. Wall-clock budget for one REFINE
            search (checked between backtracking steps). None = unbounded.
        """
        self.sentence_ids = np.asarray(sentence_ids)
        self.topic_scores = np.asarray(topic_scores, dtype=float)
        self.combined_score = np.asarray(combined_score, dtype=float)
        self.n = len(self.sentence_ids)
        self.nTopics = self.topic_scores.shape[0]
        self.cplex_threads = cplex_threads
        self.timelimit = timelimit
        self.max_repeat = max(1, int(max_repeat))
        self.refine_timelimit = refine_timelimit

        # Partition on the query's constrained attributes (paper Section 4.1).
        clust_attrs = self.topic_scores.T
        partition = _KDTreePartition(
            clust_attrs, size_threshold=size_threshold, radius_limit=radius_limit,
            rng=np.random.default_rng(rng_seed),
        )
        self.groups = partition.groups
        self.gids = sorted(self.groups)

        # Representative row per group: mean topic scores + mean combined score.
        self.repr_topic = {}
        self.repr_score = {}
        self.group_size = {}
        for gid, members in self.groups.items():
            self.repr_topic[gid] = self.topic_scores[:, members].mean(axis=1)
            self.repr_score[gid] = float(self.combined_score[members].mean())
            self.group_size[gid] = len(members)

    def n_groups(self):
        return len(self.gids)

    # -- SKETCH (paper Section 4.2.1) ---------------------------------------

    def _build_sketch_model(self, bounds, avg_len, avg_len_step):
        m = cpx.Model(name="SketchRefine_Sketch", log_output=False, cts_by_name=True)
        m.parameters.threads.set(self.cplex_threads)

        # One integer var per group, bounded by group_size * max_repeat
        # (paper's Q[R~], generalized to REPEAT K).
        rvars = {gid: m.integer_var(
                    lb=0, ub=self.group_size[gid] * self.max_repeat, name="r{}".format(gid))
                  for gid in self.gids}

        # Same constraint names as models/ex2bundle.py, so its existing
        # bound-relaxation loop works unmodified against this model.
        for j in range(self.nTopics):
            m.add_constraint(
                ct=m.sum(self.repr_topic[gid][j] * rvars[gid] for gid in self.gids) >= bounds[j][0],
                ctname="constraint_min_topic{0}".format(j),
            )
            m.add_constraint(
                ct=m.sum(self.repr_topic[gid][j] * rvars[gid] for gid in self.gids) <= bounds[j][1],
                ctname="constraint_max_topic{0}".format(j),
            )

        m.add_constraint(
            ct=m.sum(rvars[gid] for gid in self.gids) >= avg_len - avg_len_step,
            ctname="constraint_min_len",
        )
        m.add_constraint(
            ct=m.sum(rvars[gid] for gid in self.gids) <= avg_len + avg_len_step,
            ctname="constraint_max_len",
        )

        m.maximize(m.sum(self.repr_score[gid] * rvars[gid] for gid in self.gids))
        return m, rvars

    # -- REFINE (paper Section 4.2.2) ---------------------------------------

    def _augment(self, gid, state, bounds, avg_len, avg_len_step):
        """Solve refine query Q[Gj] for group `gid`: an ILP over its own
        tuples, with every other group's current contribution (`state`)
        folded into the bounds as a constant offset. Returns the selected
        local indices, or None if infeasible.
        """
        members = self.groups[gid]

        basis_count = 0.0
        basis_topic = np.zeros(self.nTopics)
        basis_score = 0.0
        for other_gid, (kind, val) in state.items():
            if other_gid == gid:
                continue
            if kind == "reduced":
                mult = val
                basis_count += mult
                basis_topic += self.repr_topic[other_gid] * mult
                basis_score += self.repr_score[other_gid] * mult
            else:  # "original"
                idxs = val
                basis_count += len(idxs)
                if idxs:
                    basis_topic += self.topic_scores[:, idxs].sum(axis=1)
                    basis_score += float(self.combined_score[idxs].sum())

        m = cpx.Model(name="SketchRefine_Refine_g{}".format(gid), log_output=False, cts_by_name=True)
        m.parameters.threads.set(self.cplex_threads)
        # integer_var (not binary) so a sentence can be picked more than
        # once when max_repeat > 1.
        yvars = {i: m.integer_var(lb=0, ub=self.max_repeat, name="y{}".format(i)) for i in members}

        for j in range(self.nTopics):
            m.add_constraint(
                ct=m.sum(self.topic_scores[j, i] * yvars[i] for i in members)
                   >= bounds[j][0] - basis_topic[j],
                ctname="constraint_min_topic{0}".format(j),
            )
            m.add_constraint(
                ct=m.sum(self.topic_scores[j, i] * yvars[i] for i in members)
                   <= bounds[j][1] - basis_topic[j],
                ctname="constraint_max_topic{0}".format(j),
            )

        m.add_constraint(
            ct=m.sum(yvars[i] for i in members) >= (avg_len - avg_len_step) - basis_count,
            ctname="constraint_min_len",
        )
        m.add_constraint(
            ct=m.sum(yvars[i] for i in members) <= (avg_len + avg_len_step) - basis_count,
            ctname="constraint_max_len",
        )

        m.maximize(m.sum(self.combined_score[i] * yvars[i] for i in members))
        m.parameters.timelimit.set(self.timelimit)

        sol = m.solve(log_output=False)
        if sol is None:
            m.end()
            return None
        # Repeat index i per its (rounded) variable value -- CPLEX MIP
        # values can carry float noise, e.g. 1.9999999998.
        selected = []
        for i in members:
            cnt = int(round(sol.get_value(yvars[i])))
            if cnt > 0:
                selected.extend([i] * cnt)
        # Fresh CPLEX model per call; release it (after extracting values,
        # since sol stays valid after end()) to avoid leaking engine memory.
        m.end()
        return selected

    def _backtrack(self, state, bounds, avg_len, avg_len_step, infeasible_gids, is_root, deadline):
        """Greedy-backtracking search (paper Algorithm 2 / Section 4.2.2 prose).

        state : dict[gid] -> ("reduced", mult) | ("original", [local idx...]).
            Partial package from the parent level; `remaining` is recomputed
            fresh each call so a group whose attempt failed in one branch
            still gets retried in a sibling branch.
        infeasible_gids : deque[gid]. Groups that have hard-failed anywhere
            so far, shared by reference, used to reprioritize the queue
            after a failure.
        is_root : True only for the outermost call. A hard failure here is
            absorbed (the group contributes nothing, paper Figure 2(e))
            instead of propagated upward.

        Returns the completed state dict, or None if every ordering failed.
        """
        remaining = [gid for gid in state if state[gid][0] == "reduced"]
        if not remaining:
            return state
        # Biggest groups first (most constraining, most likely to fail).
        remaining.sort(key=lambda gid: -self.group_size[gid])

        queue = deque(remaining)
        in_queue = set(remaining)
        tried = set()

        while queue:
            if deadline is not None and time.time() > deadline:
                raise _RefineTimeout()
            gid = queue.popleft()
            in_queue.discard(gid)
            if gid in tried:
                # Already tried at this level -- give up here.
                return None
            tried.add(gid)

            augmented = self._augment(gid, state, bounds, avg_len, avg_len_step)

            if augmented is None:
                if gid not in infeasible_gids:
                    infeasible_gids.append(gid)
                if not is_root:
                    return None
                new_state = dict(state)
                new_state[gid] = ("original", [])
                state = new_state
                continue

            new_state = dict(state)
            new_state[gid] = ("original", augmented)

            solved = self._backtrack(
                new_state, bounds, avg_len, avg_len_step, infeasible_gids, is_root=False,
                deadline=deadline,
            )
            if solved is not None:
                return solved

            # Subtree failed; reprioritize known-troublesome groups for the
            # remaining siblings. in_queue keeps membership O(1) -- a linear
            # scan here would compound badly once group counts reach the
            # thousands.
            for inf_gid in list(infeasible_gids):
                if inf_gid in in_queue:
                    queue.remove(inf_gid)
                    queue.appendleft(inf_gid)

        return None

    def _refine(self, bounds, avg_len, avg_len_step, sketch_solution):
        # Zero-multiplicity groups contribute nothing (paper Figure 2(e));
        # seed them straight to "original" with an empty selection.
        state = {
            gid: (("reduced", sketch_solution[gid]) if sketch_solution[gid] > 0 else ("original", []))
            for gid in self.gids
        }

        deadline = (
            time.time() + self.refine_timelimit if self.refine_timelimit is not None else None
        )
        try:
            result = self._backtrack(
                state, bounds, avg_len, avg_len_step, deque(), is_root=True, deadline=deadline,
            )
        except _RefineTimeout:
            result = None
        if result is None:
            raise SketchRefineInfeasible(
                "REFINE's greedy-backtracking search exhausted every group ordering "
                "without completing the package (paper Section 4.4)."
            )
        return result

    # -- Public entry point ---------------------------------------------------

    def solve(self, bounds, avg_len, avg_len_step):
        """Run SKETCH then REFINE for the given bounds.

        Returns (status, selected_sids, sketch_model):
          status : "optimal" or "infeasible".
          selected_sids : np.ndarray of sids, or None if infeasible.
          sketch_model : the SKETCH docplex Model, returned even on success
              so the caller can run its existing bound-relaxation against it
              (same constraint names as the DIRECT method).
        """
        sketch_model, rvars = self._build_sketch_model(bounds, avg_len, avg_len_step)
        sketch_model.parameters.timelimit.set(self.timelimit)
        sketch_solu = sketch_model.solve(log_output=False)

        if sketch_solu is None:
            return "infeasible", None, sketch_model

        sketch_solution = {gid: int(round(sketch_solu.get_value(rvars[gid]))) for gid in self.gids}

        try:
            final_state = self._refine(bounds, avg_len, avg_len_step, sketch_solution)
        except SketchRefineInfeasible:
            return "infeasible", None, sketch_model

        selected_local = []
        for gid, (kind, val) in final_state.items():
            assert kind == "original", (gid, kind, val)
            selected_local.extend(val)

        return "optimal", self.sentence_ids[selected_local], sketch_model
