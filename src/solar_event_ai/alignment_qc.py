"""Quality-control report for possible IRIS SJI frame-to-frame jitter."""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .iris_sji import IRISSJI
from .registration import estimate_translation, mean_abs_difference, shift_image, evaluate_translation


def alignment_check(args):
    if not args.file.is_file():
        raise FileNotFoundError(args.file)
    if args.stride < 1 or args.max_frames < 0 or args.max_shift < 1:
        raise ValueError("Invalid stride, max-frames, or max-shift")

    output = args.output.resolve()
    catalogs = output / "catalogs"
    figures = output / "figures"
    catalogs.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    stem = args.file.name.removesuffix(".gz").removesuffix(".fits")
    csv_path = catalogs / f"{stem}_alignment_check.csv"
    graph_path = figures / f"{stem}_alignment_check.png"
    comparison_path = figures / f"{stem}_alignment_example.png"
    samples = []
    chosen = None
    cumulative_y = 0
    cumulative_x = 0
    last = None

    with IRISSJI(args.file) as reader:
        for n, frame in enumerate(reader.frames(args.start, args.end)):
            if n % args.stride:
                continue
            if args.max_frames and len(samples) >= args.max_frames:
                break
            if last is None:
                samples.append({"frame": frame.index, "time_utc": frame.time_utc,
                                "step_dy_px": 0, "step_dx_px": 0,
                                "cumulative_dy_px": 0, "cumulative_dx_px": 0,
                                "phase_peak": "", "status": "reference"})
                last = frame
                continue
            try:
                dy, dx, peak = estimate_translation(
                    last.rate, frame.rate, max_shift=args.max_shift
                )
                if max(abs(dy), abs(dx)) >= args.max_shift:
                    metrics = {"status": "review", "before": float("nan"),
                               "after": float("nan"), "gain_fraction": float("nan"),
                               "overlap_fraction": float("nan")}
                else:
                    metrics = evaluate_translation(last.rate, frame.rate, dy, dx)
            except ValueError:
                dy, dx, peak = 0, 0, float("nan")
                metrics = {"status": "review", "before": float("nan"),
                           "after": float("nan"), "gain_fraction": float("nan"),
                           "overlap_fraction": float("nan")}

            status = metrics["status"]
            if status == "accepted":
                cumulative_y += dy
                cumulative_x += dx

            # Prefer showing a rejected shift in the example, otherwise
            # show the largest nonzero estimate for visual review.
            severity = (2 if status == "rejected" else 1) if (dy or dx) else 0
            ranking = (severity, abs(dy) + abs(dx))
            if severity and (chosen is None or ranking > chosen[0]):
                chosen = (ranking, last.rate.copy(), frame.rate.copy(), dy, dx,
                          last.index, frame.index, metrics)

            # Continue sequentially even if a proposed shift is rejected.
            last = frame
            samples.append({"frame": frame.index, "time_utc": frame.time_utc,
                            "step_dy_px": dy, "step_dx_px": dx,
                            "cumulative_dy_px": cumulative_y,
                            "cumulative_dx_px": cumulative_x,
                            "phase_peak": peak, "status": status,
                            "mad_before_same_mask": metrics["before"],
                            "mad_after_same_mask": metrics["after"],
                            "improvement_fraction": metrics["gain_fraction"],
                            "valid_overlap_fraction": metrics["overlap_fraction"]})

    if len(samples) < 2:
        raise ValueError("Need at least two selected frames for alignment QC")

    columns = ["frame", "time_utc", "step_dy_px", "step_dx_px",
               "cumulative_dy_px", "cumulative_dx_px", "phase_peak", "status", "mad_before_same_mask",
               "mad_after_same_mask", "improvement_fraction", "valid_overlap_fraction"]
    with csv_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(samples)

    idx = np.array([row["frame"] for row in samples])
    cy = np.array([row["cumulative_dy_px"] for row in samples])
    cx = np.array([row["cumulative_dx_px"] for row in samples])
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(idx, cx, label="Estimated cumulative dx", linewidth=1)
    ax.plot(idx, cy, label="Estimated cumulative dy", linewidth=1)
    ax.set(xlabel="Original FITS frame index", ylabel="Estimated translation (pixels)",
           title="IRIS frame-to-frame alignment QC (not a validated correction)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(graph_path, dpi=150)
    plt.close(fig)

    if chosen is not None:
        _, ref, moving, dy, dx, first_id, second_id, metrics = chosen
        corrected = shift_image(moving, dy, dx)
        valid = np.isfinite(ref) & (ref > 0)
        vmin, vmax = np.percentile(ref[valid], [2, 99])
        if vmax <= vmin:
            vmax = vmin + 1
        fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
        for ax, img, title in zip(
            axes,
            (ref, moving, corrected),
            (f"Reference: frame {first_id}", f"Unaligned: frame {second_id}",
             f"Estimated shifted: ({dy:+d}, {dx:+d}) px")
        ):
            plot = np.where(np.isfinite(img) & (img > 0), img, np.nan)
            ax.imshow(plot, origin="lower", cmap="magma", vmin=vmin, vmax=vmax)
            ax.set_title(title, fontsize=10)
        before = metrics["before"]
        after = metrics["after"]
        fig.suptitle(f"{metrics['status'].upper()} (same valid pixels) | mean absolute difference: {before:.2f} -> {after:.2f}")
        fig.savefig(comparison_path, dpi=150)
        plt.close(fig)

    counts = {status: sum(row["status"] == status for row in samples)
              for status in ("accepted", "rejected", "zero_shift", "review")}
    print(f"Frames examined: {len(samples)}; accepted nonzero: {counts['accepted']}; "
          f"rejected: {counts['rejected']}; zero-shift: {counts['zero_shift']}; "
          f"needs review: {counts['review']}")
    print("Per-frame shift report:", csv_path)
    print("Estimated translation graph:", graph_path)
    if chosen:
        print("Before/after example:", comparison_path)
    print("No raw data or candidate catalog was modified.")
    print("Do not apply these shifts automatically without checking the results.")
    return 0
