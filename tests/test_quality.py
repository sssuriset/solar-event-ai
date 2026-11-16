import numpy as np

from solar_event_ai.quality import finite_fraction


def test_all_finite():
    assert finite_fraction(np.ones((4, 4))) == 1.0


def test_missing_pixels():
    data = np.array([1.0, np.nan, 2.0, np.inf])
    assert finite_fraction(data) == 0.5


def test_empty_input():
    assert finite_fraction(np.array([])) == 0.0
