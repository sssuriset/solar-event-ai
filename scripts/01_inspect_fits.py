"""Inspect FITS metadata and generate a diagnostic image."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

parser = argparse.ArgumentParser()
parser.add_argument("file", type=Path)
parser.add_argument("--hdu", type=int, default=None)
parser.add_argument("--frame", type=int, default=0)
args = parser.parse_args()

if not args.file.is_file():
    parser.error(f"File not found: {args.file}")

output = Path("results/figures")
output.mkdir(parents=True, exist_ok=True)

with fits.open(args.file, memmap=True) as hdul:
    hdul.info()

    index = args.hdu

    if index is None:
        for i, hdu in enumerate(hdul):
            if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)):
                if hdu.data is not None and hdu.data.ndim >= 2:
                    index = i
                    break

    if index is None:
        raise ValueError("No image array found in FITS file.")

    array = hdul[index].data
    original_shape = list(array.shape)

    if array.ndim > 2:
        if args.frame < 0 or args.frame >= array.shape[0]:
            raise IndexError("Frame number is out of range.")
        array = array[args.frame]

    while array.ndim > 2:
        array = array[0]

    image = np.asarray(array, dtype=np.float32)

    primary = hdul[0].header
    header = hdul[index].header

    metadata = {
        "source_file": str(args.file),
        "hdu": index,
        "original_shape": original_shape,
        "frame": args.frame,
    }

    for key in ["INSTRUME", "TELESCOP", "DATE-OBS",
                "STARTOBS", "OBSID", "WAVELNTH"]:
        metadata[key] = header.get(key, primary.get(key))

finite = np.isfinite(image)

if not np.any(finite):
    raise ValueError("The selected image has no finite pixels.")

low, high = np.percentile(image[finite], [1, 99.5])

if high <= low:
    high = low + 1

fig, ax = plt.subplots(figsize=(8, 7))

ax.imshow(
    image,
    origin="lower",
    cmap="gray",
    vmin=low,
    vmax=high,
)

ax.set_title(args.file.name, fontsize=10)
ax.set_xlabel("Pixel X")
ax.set_ylabel("Pixel Y")

destination = output / f"{args.file.stem}_quicklook.png"

fig.savefig(destination, dpi=180, bbox_inches="tight")
plt.close(fig)

metadata_path = output / f"{args.file.stem}_metadata.json"
metadata_path.write_text(json.dumps(metadata, indent=2, default=str))

print(json.dumps(metadata, indent=2, default=str))
print("Quicklook:", destination)
print("Metadata:", metadata_path)
print("This is a diagnostic slice, not a calibrated event classification.")
