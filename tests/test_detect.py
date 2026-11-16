from dataclasses import dataclass

import numpy as np

from solar_event_ai.detect import (
    BrighteningDetector, robust_sigma
)


@dataclass
class Frame:
    index: int
    time_utc: str
    rate: np.ndarray


def test_constant_sigma():
    assert robust_sigma(np.ones(20)) == 0.0


def test_new_brightening():
    rng = np.random.default_rng(6)

    base = 100 + rng.normal(
        0, 1, (100, 100)
    ).astype("float32")

    detector = BrighteningDetector(
        threshold=4,
        min_area=3
    )

    assert detector.step(
        Frame(0, "t0", base)
    ) == []

    bright = base.copy()
    bright[40:45, 50:55] += 80

    candidates = detector.step(
        Frame(1, "t1", bright)
    )

    assert any(
        abs(c.x_px - 52) < 3
        and abs(c.y_px - 42) < 3
        for c in candidates
    )


def test_static_image():
    image = np.full(
        (40, 40), 20.0, dtype="float32"
    )

    detector = BrighteningDetector(
        threshold=5
    )

    detector.step(Frame(0, "t0", image))

    assert detector.step(
        Frame(1, "t1", image)
    ) == []
