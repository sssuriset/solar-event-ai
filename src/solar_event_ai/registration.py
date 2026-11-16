"""Experimental integer-pixel frame-to-frame translation estimator.

Diagnostic only. IRIS Level-2 SJI already has some pointing correction.
This estimator does not account for solar feature evolution, distortion,
rotation, or time-dependent WCS. Do not apply its output blindly.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, shift as ndi_shift


def _features(image):
    image = np.asarray(image, dtype=np.float32)
    if image.ndim != 2:
        raise ValueError("Expected a 2D image")
    valid = np.isfinite(image) & (image > 0)
    if valid.mean() < 0.25:
        raise ValueError("Too few valid pixels for alignment check")
    fill = float(np.median(image[valid]))
    filled = np.where(valid, image, fill)
    highpass = gaussian_filter(filled, 1.0) - gaussian_filter(filled, 8.0)
    scale = max(float(np.percentile(np.abs(highpass[valid]), 95)), 1e-4)
    clipped = np.clip(highpass / scale, -4.0, 4.0)
    window = np.outer(np.hanning(image.shape[0]), np.hanning(image.shape[1]))
    return clipped * window


def estimate_translation(reference, moving, max_shift=12):
    """Return (dy, dx, peak) to shift *moving* into the reference frame.

    Positive dy moves moving downward in array row coordinates; positive dx
    moves it right. Peak is an uncalibrated phase-correlation diagnostic,
    not a statistical confidence or a probability.
    """
    ref = np.asarray(reference)
    mov = np.asarray(moving)
    if ref.shape != mov.shape or ref.ndim != 2:
        raise ValueError("Images must be 2D with identical shapes")
    if max_shift < 1 or max_shift >= min(ref.shape) // 2:
        raise ValueError("max_shift must be positive and below half the image size")
    a = _features(ref)
    b = _features(mov)
    cross = np.fft.rfft2(a) * np.conj(np.fft.rfft2(b))
    magnitude = np.abs(cross)
    correlation = np.fft.irfft2(
        cross / np.maximum(magnitude, 1e-10), s=ref.shape
    ).real
    h, w = correlation.shape
    ys = np.rint(np.fft.fftfreq(h) * h).astype(int)
    xs = np.rint(np.fft.fftfreq(w) * w).astype(int)
    allowed = ((np.abs(ys[:, None]) <= max_shift)
               & (np.abs(xs[None, :]) <= max_shift))
    scores = np.where(allowed, correlation, -np.inf)
    y, x = np.unravel_index(np.argmax(scores), scores.shape)
    return int(ys[y]), int(xs[x]), float(correlation[y, x])


def shift_image(image, dy, dx):
    """Translate image with NaN at newly exposed boundaries (for inspection)."""
    src = np.asarray(image, dtype=np.float32)
    valid = np.isfinite(src) & (src > 0)
    filled = np.where(valid, src, 0.0)
    result = ndi_shift(filled, (dy, dx), order=1, mode="constant", cval=0.0,
                       prefilter=False)
    coverage = ndi_shift(valid.astype(np.float32), (dy, dx), order=1,
                         mode="constant", cval=0.0, prefilter=False)
    return np.where(coverage > 0.999, result, np.nan)


def mean_abs_difference(a, b):
    a, b = np.asarray(a), np.asarray(b)
    valid = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    if valid.sum() < 5:
        return float("nan")
    return float(np.mean(np.abs(a[valid] - b[valid])))


def evaluate_translation(reference, moving, dy, dx, min_gain=0.03, min_overlap=0.70):
    """Check a proposed shift on the SAME valid pixels before and after.

    Returns metrics and a descriptive decision, without changing either image.
    The intensity metric is exploratory; it is not physical validation.
    """
    ref = np.asarray(reference, dtype=np.float32)
    mov = np.asarray(moving, dtype=np.float32)
    if ref.ndim != 2 or ref.shape != mov.shape:
        raise ValueError("Images must be 2D with identical shapes")
    old_mask = np.isfinite(ref) & (ref > 0) & np.isfinite(mov) & (mov > 0)
    if old_mask.sum() < 10:
        return {"status": "review", "before": float("nan"),
                "after": float("nan"), "gain_fraction": float("nan"),
                "overlap_fraction": 0.0}
    if dy == 0 and dx == 0:
        return {"status": "zero_shift", "before": float(np.mean(np.abs(ref[old_mask] - mov[old_mask]))),
                "after": float(np.mean(np.abs(ref[old_mask] - mov[old_mask]))),
                "gain_fraction": 0.0, "overlap_fraction": 1.0}
    shifted = shift_image(mov, dy, dx)
    common = old_mask & np.isfinite(shifted) & (shifted > 0)
    overlap = float(common.sum() / old_mask.sum())
    if overlap < min_overlap or common.sum() < 10:
        return {"status": "review", "before": float("nan"),
                "after": float("nan"), "gain_fraction": float("nan"),
                "overlap_fraction": overlap}
    before = float(np.mean(np.abs(ref[common] - mov[common])))
    after = float(np.mean(np.abs(ref[common] - shifted[common])))
    gain = (before - after) / max(before, 1e-8)
    return {"status": "accepted" if gain >= min_gain else "rejected",
            "before": before, "after": after,
            "gain_fraction": float(gain), "overlap_fraction": overlap}
