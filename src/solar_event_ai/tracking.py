"""Conservative, auditable association of IRIS brightening detections over time.

Track IDs are hypotheses linking image regions, not validated solar events.
No FITS images, raw detections, or quality annotations are modified.
"""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment

REQUIRED = (
    "obsid", "frame", "time_utc", "x_px", "y_px", "area_px",
    "peak_delta_dn_s", "peak_temporal_sigma"
)


def _time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_detections(path):
    """Read candidates without changing their original values or QC flags."""
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not set(REQUIRED).issubset(reader.fieldnames):
            raise ValueError(f"Candidate CSV needs columns: {', '.join(REQUIRED)}")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    if not rows:
        raise ValueError("Candidate catalog is empty; no tracks to associate")
    obsids = {row["obsid"] for row in rows}
    if len(obsids) != 1:
        raise ValueError("One track run must contain exactly one OBSID")
    for row in rows:
        row["_frame"] = int(row["frame"])
        row["_time"] = _time(row["time_utc"])
        row["_x"] = float(row["x_px"])
        row["_y"] = float(row["y_px"])
        row["_area"] = int(row["area_px"])
        row["_peak"] = float(row["peak_delta_dn_s"])
        if (row["_frame"] < 0 or row["_area"] < 1 or
                not np.isfinite([row["_x"], row["_y"], row["_peak"]]).all()):
            raise ValueError("Invalid candidate frame, position, area, or intensity")
    rows.sort(key=lambda r: (r["_frame"], r["_time"], r["_x"], r["_y"], -r["_peak"]))
    # Reject contradictory per-frame timestamps; a unique frame must refer to one exposure.
    by_frame_time = {}
    for row in rows:
        earlier = by_frame_time.setdefault(row["_frame"], row["_time"])
        if row["_time"] != earlier:
            raise ValueError(f"Inconsistent timestamps at frame {row['_frame']}")
    ordered_frames = sorted(by_frame_time)
    if any(by_frame_time[b] <= by_frame_time[a] for a, b in zip(ordered_frames, ordered_frames[1:])):
        raise ValueError("Observation time must increase with FITS frame index")
    return rows, fieldnames


def associate(rows, *, max_distance_px=7.0, max_gap_frames=2,
              max_gap_seconds=90.0, ambiguity_margin_px=1.5):
    """Assign one detection to at most one active track per frame.

    Uses a globally minimal one-to-one distance assignment, subject to spatial,
    temporal, and frame-gap gates. No velocity extrapolation, splitting or merging.
    """
    if max_distance_px <= 0 or max_gap_frames < 1 or max_gap_seconds <= 0 or ambiguity_margin_px < 0:
        raise ValueError("Invalid association thresholds")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["_frame"]].append(row)
    tracks = []
    active = []
    for frame in sorted(grouped):
        detections = grouped[frame]
        active = [track for track in active if
                  frame - track[-1]["_frame"] <= max_gap_frames and
                  0 < (detections[0]["_time"] - track[-1]["_time"]).total_seconds() <= max_gap_seconds]
        cost = np.full((len(active), len(detections)), np.inf)
        for i, track in enumerate(active):
            last = track[-1]
            frame_gap = frame - last["_frame"]
            for j, detection in enumerate(detections):
                dt = (detection["_time"] - last["_time"]).total_seconds()
                if frame_gap < 1 or frame_gap > max_gap_frames or not 0 < dt <= max_gap_seconds:
                    continue
                distance = float(np.hypot(detection["_x"]-last["_x"], detection["_y"]-last["_y"]))
                # Allow a little more motion when an intermediate frame is missing.
                if distance <= max_distance_px * np.sqrt(frame_gap):
                    cost[i, j] = distance
        matches = []
        if cost.size and np.isfinite(cost).any():
            valid = np.isfinite(cost)
            # Explicit dummy assignments allow genuinely unmatched detections/tracks.
            penalty = max_distance_px * np.sqrt(max_gap_frames) + 1
            augmented = np.full((len(active), len(detections) + len(active)), penalty)
            augmented[:, :len(detections)] = np.where(valid, cost, 1e6)
            row_idx, col_idx = linear_sum_assignment(augmented)
            matches = [(i, j) for i, j in zip(row_idx, col_idx)
                       if j < len(detections) and np.isfinite(cost[i, j])]
        matched = set()
        for i, j in matches:
            row = detections[j]
            # Multiple possible assignments signal potentially overlapping structures.
            alternatives_for_det = np.sum(np.isfinite(cost[:, j]) &
                                          (cost[:, j] <= cost[i, j] + ambiguity_margin_px))
            alternatives_for_track = np.sum(np.isfinite(cost[i, :]) &
                                            (cost[i, :] <= cost[i, j] + ambiguity_margin_px))
            row["association_ambiguous"] = bool(alternatives_for_det > 1 or alternatives_for_track > 1)
            row["track_id"] = active[i][0]["track_id"]
            active[i].append(row)
            matched.add(j)
        for j, row in enumerate(detections):
            if j not in matched:
                row["track_id"] = f"T{len(tracks)+1:05d}"
                row["association_ambiguous"] = False
                track = [row]
                tracks.append(track)
                active.append(track)
    return tracks


def summarize(tracks, *, min_detections=2):
    if min_detections < 1:
        raise ValueError("min_detections must be >= 1")
    output = []
    for track in tracks:
        first, last = track[0], track[-1]
        span = (last["_time"] - first["_time"]).total_seconds()
        flags = set()
        flagged_count = 0
        for row in track:
            row_flags = {x for x in row.get("qc_flags", "").split(";") if x}
            flags.update(row_flags)
            flagged_count += bool(row_flags)
        ambiguous = sum(bool(row["association_ambiguous"]) for row in track)
        summary = {
            "obsid": first["obsid"], "track_id": first["track_id"],
            "first_frame": first["_frame"], "last_frame": last["_frame"],
            "start_utc": first["_time"].isoformat(), "end_utc": last["_time"].isoformat(),
            "observed_span_s": round(span, 3), "n_detections": len(track),
            "start_x_px": first["_x"], "start_y_px": first["_y"],
            "last_x_px": last["_x"], "last_y_px": last["_y"],
            "apparent_displacement_px": round(float(np.hypot(last["_x"] - first["_x"], last["_y"] - first["_y"])), 3),
            "max_area_px": max(row["_area"] for row in track),
            "max_peak_delta_dn_s": max(row["_peak"] for row in track),
            "n_qc_flagged": flagged_count, "qc_flags_any": ";".join(sorted(flags)),
            "ambiguous_associations": ambiguous,
            "review_status": ("multiple_detections_needs_review" if len(track) >= min_detections
                              else "short_track_needs_review"),
        }
        output.append(summary)
    return output


def track_catalog(args):
    """CLI operation: association, reproducible output files, and summary plot."""
    if not args.catalog.is_file():
        raise FileNotFoundError(args.catalog)
    rows, original_fields = read_detections(args.catalog)
    tracks = associate(rows, max_distance_px=args.max_distance,
                       max_gap_frames=args.max_gap_frames, max_gap_seconds=args.max_gap_seconds,
                       ambiguity_margin_px=args.ambiguity_margin)
    summaries = summarize(tracks, min_detections=args.min_detections)

    root = args.output.resolve()
    (root / "catalogs").mkdir(parents=True, exist_ok=True)
    (root / "figures").mkdir(parents=True, exist_ok=True)
    stem = args.catalog.stem
    if stem.endswith("_quality_candidates"):
        stem = stem[:-len("_quality_candidates")]
    elif stem.endswith("_candidates"):
        stem = stem[:-len("_candidates")]
    detections_file = root / "catalogs" / f"{stem}_tracked_detections.csv"
    tracks_file = root / "catalogs" / f"{stem}_event_tracks.csv"
    summary_file = root / "catalogs" / f"{stem}_track_summary.json"
    plot_file = root / "figures" / f"{stem}_track_overview.png"
    with detections_file.open("w", newline="") as file:
        columns = original_fields + ["track_id", "association_ambiguous"]
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with tracks_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    frame_counts = Counter(row["_frame"] for row in rows)
    new_track_counts = Counter(track[0]["_frame"] for track in tracks)
    frames = sorted(frame_counts)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), layout="constrained")
    axes[0].plot(frames, [frame_counts[f] for f in frames], label="Detected regions", linewidth=1)
    axes[0].plot(frames, [new_track_counts[f] for f in frames], label="New provisional tracks", linewidth=1)
    axes[0].set(ylabel="Counts per frame", title="Preliminary candidate association — NOT validated events")
    axes[0].legend()
    # Plot representative long tracks, not a cherry-picked validation result.
    examples = sorted(tracks, key=lambda t: (-len(t), t[0]["_frame"], t[0]["track_id"]))[:5]
    for track in examples:
        axes[1].plot([r["_frame"] for r in track], [r["_peak"] for r in track],
                     marker=".", linewidth=1, label=track[0]["track_id"])
    axes[1].set(xlabel="Original FITS frame index", ylabel="Peak change (reader DN/s)")
    if examples:
        axes[1].legend(loc="best", fontsize=8)
    fig.savefig(plot_file, dpi=155)
    plt.close(fig)

    meta = {
        "warning": "Preliminary associations only. Observed span is not physical lifetime. No instrument-alignment correction, event labels, or validation implied.",
        "obsid": rows[0]["obsid"],
        "source_catalog": str(args.catalog.resolve()),
        "source_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        "n_input_detections": len(rows), "n_candidate_tracks": len(tracks),
        "n_multiframe_tracks": sum(len(t) >= 2 for t in tracks),
        "n_association_ambiguous_rows": sum(bool(r["association_ambiguous"]) for r in rows),
        "n_qc_flagged_rows": sum(bool(r.get("qc_flags", "")) for r in rows),
        "parameters": {"max_distance_px": args.max_distance, "max_gap_frames": args.max_gap_frames,
                       "max_gap_seconds": args.max_gap_seconds, "min_detections": args.min_detections,
                       "ambiguity_margin_px": args.ambiguity_margin},
    }
    summary_file.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Detections: {len(rows)}; provisional tracks: {len(tracks)}; multi-frame: {meta['n_multiframe_tracks']}")
    print(f"Ambiguous association rows: {meta['n_association_ambiguous_rows']}")
    print("Tracked detections:", detections_file)
    print("Track catalog:", tracks_file)
    print("Summary:", summary_file)
    print("Figure:", plot_file)
    print("Unvalidated associations. Do not interpret as unique physical solar events.")
    return 0
