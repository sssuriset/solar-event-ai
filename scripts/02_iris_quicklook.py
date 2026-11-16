"""Inspect the 2017-05-25 IRIS 1400 A observation."""

from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]

filename = (
    "iris_l2_20170525_073324_3633105426"
    "_SJI_1400_t000.fits"
)

path = ROOT / "data/raw/iris/2017-05-25" / filename
output = ROOT / "results/figures"
output.mkdir(parents=True, exist_ok=True)

if not path.exists():
    raise FileNotFoundError(path)

start = datetime(2017, 5, 25, 7, 33, 24, tzinfo=timezone.utc)
target = datetime(2017, 5, 25, 8, 48, 0, tzinfo=timezone.utc)
target_seconds = (target - start).total_seconds()

with fits.open(
    path,
    memmap=True,
    do_not_scale_image_data=True
) as hdul:

    hdul.info()

    cube = hdul[0].data
    print("Cube shape:", cube.shape)

    if cube.ndim != 3:
        raise ValueError("Expected a 3D SJI time-series cube.")

    frame_count = cube.shape[0]
    times = None

    if len(hdul) > 1 and hdul[1].data is not None:
        auxiliary = hdul[1].data

        if (
            auxiliary.ndim == 2
            and auxiliary.shape[0] == frame_count
        ):
            candidate = np.asarray(auxiliary[:, 0], dtype=float)

            if np.all(np.isfinite(candidate)):
                times = candidate

    if times is None:
        raise ValueError(
            "Frame timestamps unavailable. Inspect the "
            "auxiliary FITS extension before selecting a frame."
        )

    frame = int(np.argmin(np.abs(times - target_seconds)))
    actual_time = start + timedelta(seconds=float(times[frame]))

    image = np.asarray(cube[frame], dtype=np.float32).copy()

finite = image[np.isfinite(image)]

if finite.size == 0:
    raise ValueError("Selected frame contains no finite pixels.")

low, high = np.percentile(finite, [1, 99.5])

if high <= low:
    high = low + 1

fig, ax = plt.subplots(figsize=(9, 8))

ax.imshow(
    image,
    origin="lower",
    cmap="magma",
    vmin=low,
    vmax=high
)

ax.set_title(
    "IRIS SJI 1400 A\n"
    + actual_time.strftime("%Y-%m-%d %H:%M:%S UTC")
)

ax.set_xlabel("Image pixel X")
ax.set_ylabel("Image pixel Y")

destination = output / "iris_20170525_0848_quicklook.png"

fig.savefig(destination, dpi=180, bbox_inches="tight")
plt.close(fig)

metadata = {
    "observation_id": "3633105426",
    "channel_angstrom": 1400,
    "cube_shape": list(cube.shape),
    "selected_frame": frame,
    "frame_time_utc": actual_time.isoformat(),
    "source_file": filename,
    "figure": str(destination),
}

metadata_file = output / "iris_20170525_quicklook.json"
metadata_file.write_text(json.dumps(metadata, indent=2))

print(json.dumps(metadata, indent=2))
print("Saved figure:", destination)
