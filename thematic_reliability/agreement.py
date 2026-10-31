"""Inter-rater reliability measures: Cohen's kappa, Krippendorff's alpha, percent agreement.

Each function takes two or more sequences of category labels applied to the same
units and returns the reliability coefficient alongside its components so downstream
code can report what drove the number.
"""

from __future__ import annotations
from itertools import combinations
from collections import Counter


def percent_agreement(coder_a: list, coder_b: list) -> float:
    """Proportion of units where two coders assigned the same label."""
    if len(coder_a) != len(coder_b):
        raise ValueError(
            "coders must label the same number of units (%d vs %d)"
            % (len(coder_a), len(coder_b))
        )
    if not coder_a:
        raise ValueError("empty coding sequence")
    return sum(a == b for a, b in zip(coder_a, coder_b)) / len(coder_a)


def cohen_kappa(
    coder_a: list, coder_b: list, categories: list | None = None
) -> tuple[float, float, float]:
    """Cohen's kappa for two coders on the same units.

    Parameters
    ----------
    coder_a, coder_b : list
        Category labels in the same unit order.
    categories : list, optional
        Explicit category set. Inferred from data when omitted.

    Returns
    -------
    kappa : float
        The kappa coefficient.
    p_observed : float
        Observed proportion of agreement.
    p_expected : float
        Agreement expected by chance.
    """
    if len(coder_a) != len(coder_b):
        raise ValueError(
            "coders must label the same number of units (%d vs %d)"
            % (len(coder_a), len(coder_b))
        )
    n = len(coder_a)
    if n == 0:
        raise ValueError("empty coding sequence")

    if categories is None:
        categories = sorted(set(coder_a) | set(coder_b))

    cat_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    matrix = [[0] * k for _ in range(k)]

    for a, b in zip(coder_a, coder_b):
        matrix[cat_idx[a]][cat_idx[b]] += 1

    p_observed = sum(matrix[i][i] for i in range(k)) / n

    p_expected = sum(
        (sum(matrix[i][j] for j in range(k)) / n)
        * (sum(matrix[j][i] for j in range(k)) / n)
        for i in range(k)
    )

    if p_expected >= 1.0:
        return 1.0, p_observed, p_expected

    kappa = (p_observed - p_expected) / (1 - p_expected)
    return kappa, p_observed, p_expected


def _coincidence_matrix(units: list[list], categories: list) -> list[list[float]]:
    """Build the coincidence matrix for Krippendorff's alpha.

    `units` is a list of coded units; each unit is a list of labels from the
    coders who rated it (missing ratings are simply absent, so lists may vary
    in length as long as each has at least two labels).
    """
    cat_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    matrix = [[0.0] * k for _ in range(k)]

    for labels in units:
        m = len(labels)
        if m < 2:
            continue
        for c, d in combinations(range(m), 2):
            ci = cat_idx[labels[c]]
            di = cat_idx[labels[d]]
            weight = 1.0 / (m - 1)
            matrix[ci][di] += weight
            matrix[di][ci] += weight

    return matrix


def krippendorff_alpha(
    units: list[list], categories: list | None = None
) -> tuple[float, float, float]:
    """Krippendorff's alpha for nominal data, any number of coders.

    Parameters
    ----------
    units : list of lists
        Each element is one unit's labels from all coders who rated it.
        Units with fewer than 2 labels are skipped (missing data is handled
        by omission, not imputation).
    categories : list, optional
        Explicit category set. Inferred from data when omitted.

    Returns
    -------
    alpha : float
        The alpha coefficient.
    d_observed : float
        Observed disagreement.
    d_expected : float
        Expected disagreement.
    """
    if categories is None:
        categories = sorted({label for u in units for label in u})

    coincidence = _coincidence_matrix(units, categories)
    k = len(categories)

    n_total = sum(sum(row) for row in coincidence)
    if n_total == 0:
        raise ValueError("no ratable units (need at least two labels per unit)")

    margin = [sum(coincidence[i]) for i in range(k)]

    d_observed = 1.0 - sum(coincidence[i][i] for i in range(k)) / n_total

    d_expected = 1.0 - sum(margin[i] * (margin[i] - 1) for i in range(k)) / (
        n_total * (n_total - 1)
    )

    if d_expected == 0:
        return 1.0, d_observed, d_expected

    alpha = 1.0 - d_observed / d_expected
    return alpha, d_observed, d_expected
