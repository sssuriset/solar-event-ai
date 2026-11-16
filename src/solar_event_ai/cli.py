"""Command-line interface for exploratory solar-event detection."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

from .detect import BrighteningDetector
from .iris_sji import IRISSJI


def build_parser():
    parser = argparse.ArgumentParser(prog="solar-ai")
    subcommands = parser.add_subparsers(dest="command", required=True)
    scan = subcommands.add_parser("scan", help="Scan an IRIS SJI FITS cube")
    scan.add_argument("file", type=Path)
    scan.add_argument("--start", help="Start UTC, e.g. 2017-05-25T08:40:00")
    scan.add_argument("--end", help="End UTC, e.g. 2017-05-25T08:55:00")
    scan.add_argument("--max-frames", type=int, default=0)
    scan.add_argument("--threshold", type=float, default=5.0)
    scan.add_argument("--min-area", type=int, default=3)
    scan.add_argument("--output", type=Path, default=Path("results"))
    scan.add_argument("--overlay-limit", type=int, default=20)
    return parser


def scan_observation(args):
    if not args.file.is_file():
        raise FileNotFoundError(args.file)
    if args.threshold <= 0 or args.min_area < 1 or args.max_frames < 0:
        raise ValueError("Threshold and min-area must be positive; max-frames must be nonnegative")
    if args.overlay_limit < 1:
        raise ValueError("overlay-limit must be positive")

    out = args.output.resolve()
    catalogs = out / "catalogs"
    figures = out / "figures"
    catalogs.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    stem = args.file.name.removesuffix(".gz").removesuffix(".fits")
    csv_path = catalogs / f"{stem}_candidates.csv"
    graph_path = figures / f"{stem}_candidate_overview.png"
    overlay_path = figures / f"{stem}_candidate_overlay.png"

    detector = BrighteningDetector(threshold=args.threshold, min_area=args.min_area)
    frame_indices = []
    counts = []
    selected = None
    candidate_total = 0
    columns = [
        "obsid", "frame", "time_utc", "x_px", "y_px", "area_px",
        "peak_delta_dn_s", "peak_temporal_sigma"
    ]
    with IRISSJI(args.file) as obs, csv_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        print(f"Observation: {obs.obsid}; available frames: {obs.nframes}")
        for frame in obs.frames(args.start, args.end, args.max_frames):
            hits = detector.step(frame)
            frame_indices.append(frame.index)
            counts.append(len(hits))
            candidate_total += len(hits)
            for hit in hits:
                writer.writerow({"obsid": obs.obsid, **vars(hit)})
            # Keep one actual observation frame for a visual sanity check.
            if hits and (selected is None or len(hits) > selected[0]):
                selected = (len(hits), frame.index, frame.time_utc,
                            frame.rate.copy(), sorted(
                                hits, key=lambda h: h.peak_temporal_sigma,
                                reverse=True)[:args.overlay_limit])
            if len(frame_indices) % 100 == 0:
                print(f"Processed {len(frame_indices)} frames; {candidate_total} candidate regions")

    if not frame_indices:
        raise ValueError("No frames matched the requested observation interval")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(frame_indices, counts, linewidth=1)
    ax.set(xlabel="Original FITS frame index", ylabel="Candidate regions per frame",
           title="Exploratory brightening detections (not validated events)")
    fig.tight_layout()
    fig.savefig(graph_path, dpi=150)
    plt.close(fig)

    if selected is not None:
        count, index, timestamp, image, hits = selected
        valid = np.isfinite(image) & (image > 0)
        if valid.any():
            low, high = np.percentile(image[valid], [1, 99.5])
            if high <= low:
                high = low + 1
            plot_image = np.where(valid, image, np.nan)
            fig, ax = plt.subplots(figsize=(9, 8))
            mappable = ax.imshow(plot_image, origin="lower", cmap="magma",
                                  vmin=low, vmax=high)
            for hit in hits:
                radius = max(3, np.sqrt(hit.area_px / np.pi) + 2)
                ax.add_patch(Circle((hit.x_px, hit.y_px), radius=radius,
                                    fill=False, edgecolor="cyan", linewidth=1.2))
            ax.set(xlabel="Image pixel X", ylabel="Image pixel Y",
                   title=f"IRIS candidate overlay: frame {index}\n{timestamp}"
                         f"\n{count} regions; top {len(hits)} marked")
            fig.colorbar(mappable, ax=ax, label="Intensity (reader output units)")
            fig.tight_layout()
            fig.savefig(overlay_path, dpi=150)
            plt.close(fig)
            print("Overlay:", overlay_path)

    print(f"Frames processed: {len(frame_indices)}")
    print(f"Candidate regions: {candidate_total}")
    print("Catalog:", csv_path)
    print("Overview:", graph_path)
    print("Unvalidated candidate detections; not identified solar events.")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return scan_observation(args)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
