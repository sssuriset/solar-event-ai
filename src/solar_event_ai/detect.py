"""Exploratory transient-brightening detection."""

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import (
    gaussian_filter, label, find_objects
)


@dataclass
class Candidate:
    frame: int
    time_utc: str
    x_px: float
    y_px: float
    area_px: int
    peak_delta_dn_s: float
    peak_temporal_sigma: float


def robust_sigma(values):
    """Estimate variability using median absolute deviation."""
    x = np.asarray(values)

    if x.size == 0:
        return 0.0

    med = np.median(x)
    return float(
        1.4826 * np.median(np.abs(x - med))
    )


class BrighteningDetector:
    """Running-background brightening detector."""

    def __init__(
        self,
        alpha=0.03,
        threshold=5.0,
        min_area=3,
        spatial_sigma_px=4.0,
        max_area=200
    ):
        self.alpha = alpha
        self.threshold = threshold
        self.min_area = min_area
        self.max_area = max_area
        self.spatial_sigma_px = spatial_sigma_px
        self.background = None

    def step(self, frame):
        image = np.asarray(frame.rate, dtype=np.float32)

        valid = np.isfinite(image) & (image > 0)

        if valid.mean() < 0.1:
            return []

        fill = float(np.median(image[valid]))
        clean = np.where(valid, image, fill)

        if self.background is None:
            self.background = clean.copy()
            return []

        if image.shape != self.background.shape:
            raise ValueError("Frame dimensions changed.")

        # Temporal brightening relative to running background
        delta = clean - self.background

        # Local brightness relative to nearby pixels
        smooth = gaussian_filter(
            clean, self.spatial_sigma_px
        )
        local = clean - smooth

        time_sigma = max(
            robust_sigma(delta[valid]), 1e-4
        )
        local_sigma = max(
            robust_sigma(local[valid]), 1e-4
        )

        # Pixels must satisfy both conditions
        mask = (
            valid
            & (delta > self.threshold * time_sigma)
            & (local > self.threshold * local_sigma)
        )

        structures, number = label(
            mask, structure=np.ones((3, 3))
        )

        candidates = []

        for index, slices in enumerate(
            find_objects(structures), start=1
        ):
            if slices is None:
                continue

            region = structures[slices] == index
            area = int(region.sum())

            if not self.min_area <= area <= self.max_area:
                continue

            ys, xs = np.nonzero(region)

            ys = ys + slices[0].start
            xs = xs + slices[1].start

            vals = delta[ys, xs]
            weights = np.maximum(vals, 0)

            candidates.append(
                Candidate(
                    frame=frame.index,
                    time_utc=frame.time_utc,
                    x_px=float(
                        np.average(xs, weights=weights)
                    ),
                    y_px=float(
                        np.average(ys, weights=weights)
                    ),
                    area_px=area,
                    peak_delta_dn_s=float(np.max(vals)),
                    peak_temporal_sigma=float(
                        np.max(vals) / time_sigma
                    )
                )
            )

        # Slowly update the background
        self.background[valid] = (
            (1 - self.alpha) * self.background[valid]
            + self.alpha * clean[valid]
        )

        return candidates
