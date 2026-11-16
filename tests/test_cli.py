"""Verify the installed command, including outside the project directory."""
import csv
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits


def run_command(tmp_path, *args):
    command = Path(sys.executable).parent / "solar-ai"
    assert command.exists(), f"Missing installed CLI: {command}"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [str(command), *map(str, args)], cwd=tmp_path,
        env=environment, text=True, capture_output=True, timeout=45
    )


def test_cli_help_outside_repository(tmp_path):
    result = run_command(tmp_path, "--help")
    assert result.returncode == 0, result.stderr
    assert "scan" in result.stdout


def test_cli_scans_synthetic_fits(tmp_path):
    data = np.full((4, 64, 64), 20.0, dtype=np.float32)
    data[1, 25:30, 29:34] += 90
    data[2, 25:30, 29:34] += 65
    primary = fits.PrimaryHDU(data)
    primary.header["STARTOBS"] = "2017-05-25T08:40:00"
    primary.header["OBSID"] = "test-observation"
    primary.header["EXPTIME"] = 1.0
    primary.header["BUNIT"] = "DN/s"
    auxiliary = fits.ImageHDU(np.array([
        [0.0, 1.0, 0.0], [10.0, 1.0, 0.0],
        [20.0, 1.0, 0.0], [30.0, 1.0, 0.0]
    ], dtype=np.float64))
    auxiliary.header["TIME"] = 0
    auxiliary.header["EXPTIMES"] = 1
    auxiliary.header["DSRCSIX"] = 2
    file = tmp_path / "synthetic.fits"
    fits.HDUList([primary, auxiliary]).writeto(file)
    result = run_command(tmp_path, "scan", file, "--output", tmp_path / "out")
    assert result.returncode == 0, result.stderr
    catalog = tmp_path / "out/catalogs/synthetic_candidates.csv"
    assert catalog.exists()
    with catalog.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, result.stdout
    assert (tmp_path / "out/figures/synthetic_candidate_overview.png").exists()
    assert (tmp_path / "out/figures/synthetic_candidate_overlay.png").exists()
