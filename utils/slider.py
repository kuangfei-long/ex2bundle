"""
Slider interface math (Paper Section 4.1.3).

Implements the bidirectional mapping between the user-facing slider parameter
gamma in [-beta, beta] and the underlying constraint bounds (lb_j, ub_j):

  - bounds_to_slider_params(...): given (lb, ub), pre-compute slope/offset
    so a slider centred at 0 reproduces (lb, ub).
  - slider_to_bounds(...): given gamma, produce new bounds.

This is used by the interactive demo and the slider-aware Ex2Bundle model in
``models/ex2bundle_slider.py``.
"""

import numpy as np


# Default tuning constants (see Section 5.1.1).
DEFAULT_BETA = 98     # max gamma magnitude
DEFAULT_ALPHA = 0.1   # min allowable bound width


def bounds_to_slider_params(lb, ub, alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA):
    """Compute (center_offset, center_slope, bound_offset, bound_slope) for one feature.

    These four numbers fully describe how the slider value gamma is converted
    back to (lb, ub) for that feature.

    Maps to Eqs in Section 4.1.3:
      b_I = (lb + ub) / 2
      w_I = (ub - lb - alpha/2) / (2*beta)
      b_B = (ub - lb) / 2
      w_B = (ub - lb - alpha) / (2*beta)
    """
    center_offset = (ub + lb) / 2.0                       # b_I
    center_slope  = (ub - lb - alpha / 2.0) / (2.0 * beta)  # w_I
    bound_offset  = (ub - lb) / 2.0                       # b_B
    bound_slope   = (ub - lb - alpha) / (2.0 * beta)        # w_B
    return center_offset, center_slope, bound_offset, bound_slope


def slider_to_bounds(gamma, slider_params):
    """Compute (lb, ub) for a single feature given its slider value gamma.

    `slider_params` is a 4-tuple as returned by `bounds_to_slider_params`.
    Applies:
      f_I(gamma) = w_I * gamma + b_I
      f_B(gamma) = |w_B * gamma| + b_B    (no, it's b_B - |w_B * gamma|; see paper)
    Implementation follows the deployed server code, which uses
      bound_offset = b_B - |w_B * gamma|
    so that pushing the slider to extremes narrows the band toward the chosen end.
    """
    center_offset, center_slope, bound_offset, bound_slope = slider_params
    center = center_slope * gamma + center_offset
    band   = bound_offset - abs(bound_slope * gamma)
    lb = max(0.0, center - band)
    ub = center + band
    return lb, ub


def make_slider_params_for_bounds(bounds, alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA):
    """Convenience wrapper that builds a dict shaped like the production server expects.

    bounds: array of shape (nTopics, 2), columns = (lb, ub).
    Returns dict with keys: center_offsets, center_slopes, bound_offsets, bound_slopes
    (all length-nTopics arrays).
    """
    center_offsets, center_slopes, bound_offsets, bound_slopes = [], [], [], []
    for lb, ub in bounds:
        co, cs, bo, bs = bounds_to_slider_params(lb, ub, alpha=alpha, beta=beta)
        center_offsets.append(co)
        center_slopes.append(cs)
        bound_offsets.append(bo)
        bound_slopes.append(bs)
    return {
        "center_offsets": np.array(center_offsets),
        "center_slopes":  np.array(center_slopes),
        "bound_offsets":  np.array(bound_offsets),
        "bound_slopes":   np.array(bound_slopes),
        "alpha": alpha,
        "beta":  beta,
    }


def calculate_bounds_from_slider(topic_idx, gamma, slider_values_dict):
    """Replicates the server-side `calculateBoundsFromImportanceScore` API."""
    co = slider_values_dict["center_offsets"][topic_idx]
    cs = slider_values_dict["center_slopes"][topic_idx]
    bo = slider_values_dict["bound_offsets"][topic_idx]
    bs = slider_values_dict["bound_slopes"][topic_idx]
    return slider_to_bounds(gamma, (co, cs, bo, bs))
