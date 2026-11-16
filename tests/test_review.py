"""End-to-end test: scan + visual review through the installed CLI."""
import csv
import os
import subprocess
import sys

import numpy as np
from astropy.io import fits


def test_temporal_review_from_cli(tmp_path):
    data = np.full((8, 64, 64), 20.0, dtype=np.float32)
    data[3, 25:30, 29:34] += 90
    data[4, 25:30, 29:34] += 70
    primary = fits.PrimaryHDU(data)
    primary.header["STARTOBS"] = "2017-05-25T08:40:00"
    primary.header["OBSID"] = "test-observation"
    primary.header["EXPTIME"] = 1.0
    primary.header["BUNIT"] = "DN/s"
    aux = fits.ImageHDU(np.array([[float(i * 10), 1.0, 0.0] for i in range(8)]))
    aux.header["TIME"] = 0
    aux.header["EXPTIMES"] = 1
    aux.header["DSRCSIX"] = 2
    path = tmp_path / "sample.fits"
    fits.HDUList([primary, aux]).writeto(path)
    output = tmp_path / "out"
    executable = str((__import__("pathlib").Path(sys.executable).parent / "solar-ai"))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for args in (
        ["scan", str(path), "--output", str(output)],
        ["review", str(path), "--catalog", str(output / "catalogs/sample_candidates.csv"),
         "--output", str(output), "--max-examples", "2", "--crop-radius", "10", "--edge-margin", "5", "--offset-frames", "1"],
    ):
        result = subprocess.run([executable, *args], cwd=tmp_path, env=env,
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, (result.stdout, result.stderr)
    assert (output / "figures/sample_temporal_review.png").exists()
    manifest = output / "catalogs/sample_review_manifest.csv"
    with manifest.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert all(row["reviewer_label"] == "" for row in rows)
