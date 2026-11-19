"""Integration test: installed solar-ai command works outside repository."""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def test_tracking_outside_repo(tmp_path):
    path = tmp_path / "synthetic_candidates.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["obsid","frame","time_utc","x_px","y_px","area_px",
                         "peak_delta_dn_s","peak_temporal_sigma","qc_flags"])
        for frame, x in [(1, 10), (2, 11), (3, 12), (8, 70)]:
            writer.writerow(["synthetic",frame,f"2026-01-01T00:00:{frame*5:02d}+00:00",
                             x,20,9,70,8,"" if frame != 8 else "near_image_edge"])
    exe = Path(sys.executable).parent / "solar-ai"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    run = subprocess.run([str(exe), "track", "--catalog", str(path),
                          "--output", str(tmp_path / "results")],
                         cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, (run.stdout, run.stderr)
    out = tmp_path / "results" / "catalogs"
    with (out / "synthetic_event_tracks.csv").open() as stream:
        records = list(csv.DictReader(stream))
    assert sorted(int(x["n_detections"]) for x in records) == [1, 3]
    with (out / "synthetic_tracked_detections.csv").open() as stream:
        dets = list(csv.DictReader(stream))
    assert len(dets) == 4
    assert json.loads((out / "synthetic_track_summary.json").read_text())["n_candidate_tracks"] == 2
    assert (tmp_path / "results" / "figures" / "synthetic_track_overview.png").is_file()
