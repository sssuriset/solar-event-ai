# IRIS residual-jitter audit — exploratory v0.1

Run `solar-ai align-check path/to/sji.fits --start ... --end ...`.

The command **only measures** image-to-image shifts. It does not modify the
original FITS file, alter the candidate catalog, or automatically register
images for event detection. The `alignment_check.csv` report contains the
estimated translation required to move each frame onto the preceding
*accepted* frame, plus cumulative estimates. A correlation maximum at the
search-window boundary is labeled `review` and is excluded from accumulation.

The estimator uses high-pass filtered images, a Hann window, and phase
cross-correlation. It returns integer-pixel translations only. The `phase_peak`
column is an internal algorithm diagnostic, *not* a probability or confidence
level. The estimated cumulative translation can drift as errors accumulate,
solar features evolve, or raster pointing changes.

IRIS Level 2 slit-jaw images have some pointing corrections already; their
per-exposure pointing is stored in FITS auxiliary information. The motion
of slit/field boundaries need not equal the motion of solar features.
This v0.1 method does not use the auxiliary X/Y pointing coordinates,
account for spatial distortion or differential rotation, remove dust or
slit artifacts, or validate against independently tracked features.

**Before applying a correction to science data**, compare this result with
per-exposure WCS/pointing, examine the before/after images, assess whether
registered real features sharpen without artificial duplication, and test
whether candidate detections become more stable.

Resources:
- https://interface-region-imaging-spectrograph.readthedocs.io/en/latest/_autosummary/iris.sji.SlitJawObservation.html
- https://pyoung.org/quick_guides/iris_guide.html
