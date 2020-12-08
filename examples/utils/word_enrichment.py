from typing import Iterable, List, Optional

import numpy as np
from scipy import stats, sparse


def hypergeom_p_values(
    data: np.ndarray, selected: np.ndarray
) -> List[List[float]]:
    """
    Calculates p_values using Hypergeometric distribution for two numpy arrays.
    Works on a matrices containing zeros and ones. All other values are
    truncated to zeros and ones.

    Parameters
    ----------
    data
        all examples in rows, theirs features in columns.
    selected
        selected examples in rows, theirs features in columns.

    Returns
    -------
    p-values for features
    """

    def col_sum(x):
        if sparse.issparse(x):
            return np.squeeze(np.asarray(x.sum(axis=0)))
        else:
            return np.sum(x, axis=0)

    if data.shape[1] != selected.shape[1]:
        raise ValueError("Number of columns does not match.")

    # clip values to a binary variables
    data = data > 0
    selected = selected > 0

    num_features = selected.shape[1]
    pop_size = data.shape[0]  # population size = number of all data examples
    sam_size = selected.shape[0]  # sample size = number of selected examples
    pop_counts = col_sum(
        data
    )  # number of observations in population = occurrences of words all data
    sam_counts = col_sum(
        selected
    )  # num of observations in sample = occurrences of words in selected data
    step = 250
    p_vals = []

    for i, (pc, sc) in enumerate(zip(pop_counts, sam_counts)):
        hyper = stats.hypergeom(pop_size, pc, sam_size)
        # since p-value is probability of equal to or "more extreme" than what
        # was actually observed we calculate it as 1 - cdf(sc-1). sf is survival
        # function defined as 1-cdf.
        p_vals.append(hyper.sf(sc - 1))
    return p_vals


def FDR(
    p_values: Iterable,
    dependent: bool = False,
    m: Optional[int] = None,
    ordered: bool = False,
) -> Iterable:
    """
    `False Discovery Rate <http://en.wikipedia.org/wiki/False_discovery_rate>`_
    correction on a list of p-values.

    Parameters
    ----------
    p_values
        p-values.
    dependent
        use correction for dependent hypotheses
    m
        number of hypotheses tested (default ``len(p_values)``).
    ordered
        prevent sorting of p-values if they are already sorted

    Returns
    -------
    FDR values for provided p-values
    """
    if p_values is None or len(p_values) == 0 or (m is not None and m <= 0):
        return None

    is_list = isinstance(p_values, list)
    p_values = np.array(p_values)
    if m is None:
        m = len(p_values)
    if not ordered:
        ordered = (np.diff(p_values) >= 0).all()
        if not ordered:
            indices = np.argsort(p_values)
            p_values = p_values[indices]

    if dependent:  # correct q for dependent tests
        m *= sum(1 / np.arange(1, m + 1))

    fdrs = (p_values * m / np.arange(1, len(p_values) + 1))[::-1]
    fdrs = np.array(np.minimum.accumulate(fdrs)[::-1])
    if not ordered:
        fdrs[indices] = fdrs.copy()
    return fdrs if not is_list else list(fdrs)
