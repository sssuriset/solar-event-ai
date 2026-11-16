"""Memory-efficient reader for IRIS Level 2 slit-jaw sequences."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits


@dataclass
class SJIFrame:
    index: int
    time_utc: str
    rate: np.ndarray
    exposure_s: float


def parse_utc(value):
    dt = datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class IRISSJI:
    """Read frames without loading the entire FITS cube."""

    def __init__(self, path):
        self.path = Path(path)
        self.hdul = None

    def __enter__(self):
        self.hdul = fits.open(
            self.path,
            memmap=True,
            do_not_scale_image_data=True
        )

        primary = self.hdul[0]

        if primary.data is None or primary.data.ndim != 3:
            self.hdul.close()
            raise ValueError("Expected a 3D IRIS SJI cube.")

        self.data = primary.data
        h = primary.header

        self.nframes = self.data.shape[0]
        self.obsid = str(h.get("OBSID", "unknown"))
        self.start = parse_utc(
            h.get("STARTOBS", h.get("DATE_OBS"))
        )

        self.bscale = float(h.get("BSCALE", 1.0))
        self.bzero = float(h.get("BZERO", 0.0))
        self.bunit = str(h.get("BUNIT", "Corrected DN"))
        self.fallback_exposure = float(
            h.get("EXPTIME", 1.0)
        )

        if len(self.hdul) < 2 or self.hdul[1].data is None:
            self.hdul.close()
            raise ValueError("Missing auxiliary metadata.")

        aux_header = self.hdul[1].header
        aux = self.hdul[1].data

        if (
            aux.ndim != 2
            or aux.shape[0] != self.nframes
            or "TIME" not in aux_header
        ):
            self.hdul.close()
            raise ValueError("Invalid SJI auxiliary metadata.")

        def column(name):
            if name not in aux_header:
                return None
            index = int(aux_header[name])
            return np.asarray(
                aux[:, index], dtype=float
            )

        self.offsets = column("TIME")
        self.exposures = column("EXPTIMES")
        self.sources = column("DSRCSIX")

        return self

    def __exit__(self, exc_type, exc, tb):
        if self.hdul is not None:
            self.hdul.close()

    def frames(self, start=None, end=None, max_frames=0):
        start_time = parse_utc(start) if start else None
        end_time = parse_utc(end) if end else None

        count = 0

        for i, seconds in enumerate(self.offsets):
            if not np.isfinite(seconds):
                continue

            time = self.start + timedelta(
                seconds=float(seconds)
            )

            if start_time and time < start_time:
                continue

            if end_time and time > end_time:
                continue

            if self.sources is not None:
                if self.sources[i] < 0:
                    continue

            exposure = (
                float(self.exposures[i])
                if self.exposures is not None
                else self.fallback_exposure
            )

            if not np.isfinite(exposure) or exposure <= 0:
                continue

            raw = np.asarray(
                self.data[i], dtype=np.float32
            )

            scaled = raw * self.bscale + self.bzero

            if "/s" not in self.bunit.lower():
                scaled = scaled / exposure

            yield SJIFrame(
                index=i,
                time_utc=time.isoformat(),
                rate=scaled,
                exposure_s=exposure
            )

            count += 1

            if max_frames and count >= max_frames:
                break
