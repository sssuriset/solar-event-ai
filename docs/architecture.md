# Solar Event AI architecture (v0.1)

The project is an exploratory solar-physics processing pipeline.

- `src/solar_event_ai/iris_sji.py`: read IRIS Level 2 SJI frames, timestamps and auxiliary information.
- `src/solar_event_ai/detect.py`: score localized brightening regions against temporal background and local spatial contrast.
- `src/solar_event_ai/cli.py`: installed command-line workflow, catalogs, activity graph and detection overlay.
- `src/solar_event_ai/quality.py`: numerical quality checks.
- `tests/`: algorithm and installed-command verification, using synthetic data.
- `data/raw/`: local source observations, excluded from Git.
- `results/`: local CSVs and plots, excluded from Git.

## Installed entry point

`solar-ai scan FILE.fits --start 2017-05-25T08:40:00 --end 2017-05-25T08:55:00`

The command is installed by `python -m pip install -e '.[dev]'` and works without manually setting `PYTHONPATH`.

## Scientific scope and known limitations

The output is a list of candidate regions **per frame**, not distinct physical events.
Thresholds have not been calibrated to instrumental noise. The relative temporal score is not a statistical p-value.
The program does not yet register frames, track events across time, calibrate full spatial coordinates,
independently validate exposure normalization and artifact flags against the mission documentation,
or infer an event type or physical mechanism.

The overlay is a visual quality-control diagnostic, not a labeled reference catalog.
Do not report raw candidate counts as event rates.

Next: inspect candidate overlays, audit metadata/calibration, register frames, track events,
and evaluate against independent expert-reviewed reference events.
