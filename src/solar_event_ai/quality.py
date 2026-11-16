"""Basic observational data quality checks."""

import numpy as np


def finite_fraction(data):
    """Fraction of pixels containing finite values."""
    array = np.asarray(data)

    if array.size == 0:
        return 0.0

    return float(np.count_nonzero(np.isfinite(array)) / array.size)
