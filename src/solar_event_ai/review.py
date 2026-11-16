"""Visual quality-control comparison for candidate solar brightenings.

This intentionally does not assign event classes or infer physical mechanisms.
"""

import csv
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

from .iris_sji import IRISSJI


def _read_candidates(path):
    with Path(path).open(newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"frame", "time_utc", "x_px", "y_px", "area_px", "peak_temporal_sigma"}
    if rows and not required.issubset(rows[0]):
        raise ValueError("Catalog does not have the expected candidate columns")
    return rows


def _choose_examples(rows, shape, count, edge_margin):
    height, width = shape
    usable = []
    for row in rows:
        try:
            frame = int(row["frame"])
            x, y = float(row["x_px"]), float(row["y_px"])
            score = float(row["peak_temporal_sigma"])
        except (ValueError, TypeError, KeyError):
            continue
        if not np.isfinite([x, y, score]).all():
            continue
        if not (edge_margin <= x < width - edge_margin and edge_margin <= y < height - edge_margin):
            continue
        usable.append((frame, -score, row))

    if not usable:
        return []

    # Spread examples through the scan instead of displaying only its largest peak.
    by_frame = {}
    for frame, negative_score, row in sorted(usable, key=lambda x: (x[0], x[1])):
        by_frame.setdefault(frame, row)
    frame_numbers = sorted(by_frame)
    indices = np.linspace(0, len(frame_numbers) - 1, min(count, len(frame_numbers)))
    chosen = []
    for idx in np.rint(indices).astype(int):
        row = by_frame[frame_numbers[idx]]
        if row not in chosen:
            chosen.append(row)
    return chosen


def _crop(image, x, y, radius):
    xi, yi = int(round(x)), int(round(y))
    y0, y1 = max(0, yi - radius), min(image.shape[0], yi + radius + 1)
    x0, x1 = max(0, xi - radius), min(image.shape[1], xi + radius + 1)
    crop = np.asarray(image[y0:y1, x0:x1], dtype=np.float32).copy()
    crop[~np.isfinite(crop) | (crop <= 0)] = np.nan
    return crop, x0, y0


def review_candidates(args):
    if args.max_examples < 1 or args.offset_frames < 1 or args.crop_radius < 5:
        raise ValueError("max-examples and offset-frames must be positive; crop-radius >= 5")
    if not args.file.is_file():
        raise FileNotFoundError(args.file)
    if not args.catalog.is_file():
        raise FileNotFoundError(args.catalog)

    rows = _read_candidates(args.catalog)
    output = args.output.resolve()
    figures = output / "figures"
    catalogs = output / "catalogs"
    figures.mkdir(parents=True, exist_ok=True)
    catalogs.mkdir(parents=True, exist_ok=True)
    stem = args.file.name.removesuffix(".gz").removesuffix(".fits")
    figure_path = figures / f"{stem}_temporal_review.png"
    manifest_path = catalogs / f"{stem}_review_manifest.csv"

    with IRISSJI(args.file) as obs:
        examples = _choose_examples(
            rows, obs.data.shape[-2:], args.max_examples, args.edge_margin
        )
        if not examples:
            raise ValueError("No candidates remain after edge filtering. Try --edge-margin 0")

        # The same fixed detector position is shown before, at, and after each detection.
        requested = {}
        for row in examples:
            frame_id = int(row["frame"])
            for label, i in (
                ("Before", frame_id - args.offset_frames),
                ("Detected", frame_id),
                ("After", frame_id + args.offset_frames),
            ):
                if 0 <= i < obs.nframes:
                    requested[i] = None

        needed = set(requested)
        frames = {}
        # Limit decoding to the relevant observation window, not all 4,000 frames.
        earliest = min(needed)
        latest = max(needed)
        lower = obs.start + timedelta(seconds=float(obs.offsets[earliest]) - 1)
        upper = obs.start + timedelta(seconds=float(obs.offsets[latest]) + 1)
        for frame in obs.frames(lower.isoformat(), upper.isoformat()):
            if frame.index in needed:
                frames[frame.index] = frame

        figure, axs = plt.subplots(
            len(examples), 3, figsize=(10.5, max(3, len(examples) * 2.5)),
            squeeze=False, layout="constrained"
        )
        review_rows = []
        for row_idx, candidate in enumerate(examples):
            idx = int(candidate["frame"])
            x, y = float(candidate["x_px"]), float(candidate["y_px"])
            frame_ids = [idx - args.offset_frames, idx, idx + args.offset_frames]
            panels = []
            for i in frame_ids:
                if i in frames:
                    crop, x0, y0 = _crop(frames[i].rate, x, y, args.crop_radius)
                    panels.append((crop, x0, y0, frames[i].time_utc))
                else:
                    panels.append(None)

            all_valid = [p[0][np.isfinite(p[0])] for p in panels if p is not None]
            all_valid = [v for v in all_valid if v.size]
            if all_valid:
                valid = np.concatenate(all_valid)
                vmin, vmax = np.percentile(valid, [2, 99])
                if vmax <= vmin:
                    vmax = vmin + 1
            else:
                vmin, vmax = 0, 1

            for column, (label, panel) in enumerate(zip(["Before", "Detected", "After"], panels)):
                ax = axs[row_idx, column]
                if panel is None:
                    ax.text(.5, .5, "Frame unavailable", ha="center", va="center", transform=ax.transAxes)
                    ax.set_axis_off()
                    continue
                crop, x0, y0, timestamp = panel
                ax.imshow(crop, cmap="magma", origin="lower", vmin=vmin, vmax=vmax)
                ax.add_patch(Circle((x - x0, y - y0), 4, fill=False, ec="cyan", lw=1.25))
                ax.set_title(f"{label}: {timestamp[11:19]} UTC", fontsize=9)
                ax.set_xticks([])
                ax.set_yticks([])
                if column == 0:
                    ax.set_ylabel(f"Frame {idx}  |  ({x:.0f}, {y:.0f})", fontsize=9)
            review_rows.append({
                "frame": idx, "time_utc": candidate["time_utc"],
                "x_px": candidate["x_px"], "y_px": candidate["y_px"],
                "area_px": candidate["area_px"],
                "peak_temporal_sigma": candidate["peak_temporal_sigma"],
                "reviewer_label": "", "notes": ""
            })

        figure.suptitle(
            "IRIS candidates across time — inspection only\n"
            "Same pixel position; no image registration or event classification",
            fontsize=12
        )
        figure.savefig(figure_path, dpi=150)
        plt.close(figure)

    with manifest_path.open("w", newline="") as out:
        columns = ["frame", "time_utc", "x_px", "y_px", "area_px", "peak_temporal_sigma", "reviewer_label", "notes"]
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        writer.writerows(review_rows)
    print(f"Candidate rows in catalog: {len(rows)}")
    print(f"Examples selected for review: {len(review_rows)}")
    print("Temporal review:", figure_path)
    print("Blank review manifest:", manifest_path)
    print("Do not infer event persistence or a physical mechanism without registration and validation.")
    return 0
