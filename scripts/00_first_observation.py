"""Load and visualize a real SDO/AIA observation."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import sunpy.map
from sunpy.data import sample

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "figures"
OUTPUT.mkdir(parents=True, exist_ok=True)

print("Loading SDO/AIA 171 Angstrom sample data...")

observation = sunpy.map.Map(sample.AIA_171_IMAGE)

print("Instrument:", observation.instrument)
print("Date:", observation.date.isot)
print("Dimensions:", observation.data.shape)
print("Wavelength:", observation.wavelength)

fig = plt.figure(figsize=(9, 8))
ax = fig.add_subplot(111, projection=observation)

observation.plot(axes=ax)
ax.set_title("SDO/AIA 171 Angstrom - Sample Observation")

file_path = OUTPUT / "first_solar_observation.png"

fig.savefig(file_path, dpi=180, bbox_inches="tight")
plt.close(fig)

print("Figure saved to:", file_path)
