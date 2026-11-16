"""Scan IRIS SJI observations for candidate brightenings."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solar_event_ai.iris_sji import IRISSJI
from solar_event_ai.detect import BrighteningDetector


parser = argparse.ArgumentParser(description=__doc__)

parser.add_argument("files", nargs="+", type=Path)
parser.add_argument("--start", help="UTC start time")
parser.add_argument("--end", help="UTC end time")
parser.add_argument("--max-frames", type=int, default=0)
parser.add_argument("--threshold", type=float, default=5.0)
parser.add_argument("--min-area", type=int, default=3)

args = parser.parse_args()

if (
    args.threshold <= 0
    or args.min_area < 1
    or args.max_frames < 0
):
    parser.error("Invalid detector settings.")

ROOT = Path(__file__).resolve().parents[1]

output = ROOT / "results/catalogs"
figdir = ROOT / "results/figures"

output.mkdir(parents=True, exist_ok=True)
figdir.mkdir(parents=True, exist_ok=True)

for file in args.files:

    if not file.is_file():
        print("File not found:", file)
        continue

    detector = BrighteningDetector(
        threshold=args.threshold,
        min_area=args.min_area
    )

    name = file.name.removesuffix(".gz").removesuffix(".fits")

    csvpath = output / (name + "_candidates.csv")
    figpath = figdir / (name + "_candidate_overview.png")

    counts = []
    nframes = 0
    ncandidates = 0

    with IRISSJI(file) as obs, csvpath.open(
        "w", newline=""
    ) as f:

        columns = [
            "obsid",
            "frame",
            "time_utc",
            "x_px",
            "y_px",
            "area_px",
            "peak_delta_dn_s",
            "peak_temporal_sigma"
        ]

        writer = csv.DictWriter(
            f, fieldnames=columns
        )
        writer.writeheader()

        print("Scanning:", file)
        print("Observation ID:", obs.obsid)
        print("Total frames:", obs.nframes)

        for frame in obs.frames(
            args.start,
            args.end,
            args.max_frames
        ):
            hits = detector.step(frame)

            nframes += 1
            ncandidates += len(hits)
            counts.append(len(hits))

            for hit in hits:
                writer.writerow({
                    "obsid": obs.obsid,
                    **vars(hit)
                })

            if nframes % 100 == 0:
                print(
                    f"Processed {nframes} frames, "
                    f"{ncandidates} candidate regions"
                )

    if counts:
        fig, ax = plt.subplots(
            figsize=(11, 3.5)
        )

        ax.plot(
            range(len(counts)),
            counts,
            linewidth=1
        )

        ax.set_xlabel(
            "Processed frame (chronological order)"
        )
        ax.set_ylabel(
            "Candidate regions per frame"
        )
        ax.set_title(
            "IRIS transient-brightening candidates"
        )

        fig.tight_layout()
        fig.savefig(figpath, dpi=150)
        plt.close(fig)

        print("Figure:", figpath)

    print("Frames processed:", nframes)
    print("Candidate regions:", ncandidates)
    print("Catalog:", csvpath)
    print(
        "Results are unvalidated candidate detections."
    )
