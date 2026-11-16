"""Scientific sanity tests for integer-pixel registration estimator."""
import numpy as np
from scipy.ndimage import shift

from solar_event_ai.registration import (
    estimate_translation, mean_abs_difference, shift_image
)


def _scene():
    rng = np.random.default_rng(27)
    yy, xx = np.mgrid[:192, :192]
    data = 15 + 0.5 * rng.normal(size=(192, 192))
    for x, y, amp, sigma in [(34, 42, 38, 4), (101, 118, 44, 7),
                             (79, 77, 31, 3), (154, 126, 50, 6), (60, 145, 26, 4)]:
        data += amp * np.exp(-((xx-x)**2 + (yy-y)**2) / (2*sigma**2))
    return data.astype(np.float32)


def test_known_translation():
    reference = _scene()
    moving = shift(reference, (3, -5), order=1, mode="constant", cval=0)
    dy, dx, _ = estimate_translation(reference, moving, max_shift=10)
    assert (dy, dx) == (-3, 5)
    corrected = shift_image(moving, dy, dx)
    assert mean_abs_difference(reference, corrected) < mean_abs_difference(reference, moving)


def test_zero_shift():
    reference = _scene()
    dy, dx, _ = estimate_translation(reference, reference, max_shift=10)
    assert (dy, dx) == (0, 0)


def test_reject_shape_mismatch():
    import pytest
    with pytest.raises(ValueError, match="identical shapes"):
        estimate_translation(np.ones((50, 50)), np.ones((50, 40)))
