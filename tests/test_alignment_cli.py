"""An end-to-end command test against a tiny synthetic IRIS-like FITS cube."""
import csv
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import shift
from astropy.io import fits


def test_alignment_check_from_outside_repo(tmp_path):
    rng = np.random.default_rng(12)
    y, x = np.mgrid[:96, :96]
    base = 10.0 + rng.normal(0, 0.1, (96, 96))
    for xc, yc in [(21, 30), (69, 68), (30, 74), (63, 24)]:
        base += 40 * np.exp(-((x-xc)**2+(y-yc)**2)/30)
    data = np.stack([base, shift(base, (2, -1), cval=0, mode="constant")])
    header = fits.PrimaryHDU(data)
    header.header["STARTOBS"] = "2017-05-25T08:40:00"
    header.header["OBSID"] = "synthetic"
    header.header["BUNIT"] = "DN/s"
    aux = fits.ImageHDU(np.array([[0., 1., 0.], [10., 1., 0.]]))
    aux.header["TIME"] = 0
    aux.header["EXPTIMES"] = 1
    aux.header["DSRCSIX"] = 2
    sample = tmp_path / "test.fits"
    fits.HDUList([header, aux]).writeto(sample)
    command = Path(sys.executable).parent / "solar-ai"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [str(command), "align-check", str(sample), "--output", str(tmp_path / "out")],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=45
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    report = tmp_path / "out/catalogs/test_alignment_check.csv"
    assert report.exists()
    with report.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert (int(rows[1]["step_dy_px"]), int(rows[1]["step_dx_px"])) == (-2, 1)
    assert (tmp_path / "out/figures/test_alignment_check.png").exists()
