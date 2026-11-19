# Phase 3: Provisional temporal candidate association

This module links *detected image regions*, not physically established solar events.

## Command

```bash
solar-ai track --catalog results/catalogs/<observation>_quality_candidates.csv
```

If Phase 2 QC has not been run yet, use `<observation>_candidates.csv` instead.
Input contains OBSID, frame, UTC time, pixel centroids, area, and peak image intensity change.

## Algorithm

- Sort detections by FITS frame number and observation time.
- Maintain active tracks; compare to detections in later frames within a frame/time gap.
- Gate possible matches on centroid separation in pixel coordinates.
- Use minimum-cost one-to-one assignment to prevent one detection from being assigned twice.
- Retain single-frame tracks and preserve all original quality flags.
- Mark assignments with nearby competing alternatives as ambiguous.
- No image warping, WCS coordinate conversion, spectral information, or event taxonomy.

The chosen thresholds (7 pixel gate, 2 frames, 90 seconds) are provisional. IRIS motion and
scene evolution may create false links, missed links, merged events, or fragmented tracks.

## Outputs

- `*_tracked_detections.csv`: every source detection plus track ID and ambiguous flag.
- `*_event_tracks.csv`: provisional track summary. `observed_span_s` is the difference
  between first and last detections, **not** a measurement of true physical event lifetime.
- `*_track_summary.json`: source SHA-256, thresholds, counts.
- `*_track_overview.png`: region counts and illustrative peak-change light curves.

All original observations, detector outputs, and Phase 2 annotations remain unchanged.

## Validation still required

Review examples against aligned frame movies; test crossovers, splits and merges; compare
with expert annotations on independent observations. No track count should be reported as a
confirmed number of solar events before these checks.
