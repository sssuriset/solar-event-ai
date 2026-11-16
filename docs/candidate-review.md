# Candidate review protocol (exploratory)

The `solar-ai review` command selects a small set of candidate regions spread through an observation and creates three-panel cutouts. For each selected candidate, the **same pixel position** is displayed a fixed number of frames before, at, and after the detection. The intensity color scale is held fixed within each row.

Run the detector first, then pass its CSV catalog and source FITS file to `solar-ai review`.

Outputs are a PNG temporal review sheet and a blank CSV annotation manifest. Enter `likely real brightening`, `likely artifact`, or `uncertain` under `reviewer_label`; add evidence to `notes`. These are provisional visual judgments, **not** physical event classes or confirmed reference labels.

## Important limitations

- Frames are not co-registered. Apparent motion or brightness can be caused by pointing drift.
- The three cutouts use the same pixel center, which may not track a moving solar feature.
- The examples are spread across frames and favor high-scoring regions within those frames; this is **not** a representative random sample or a performance estimate.
- Strong white pixels, edge artifacts, and transient noise should be treated skeptically.
- No pixel-level instrumental quality calibration, spectroscopy, or magnetic context is applied.
- Do not calculate precision/recall or event rates from this informal sheet.

Next: quantify pointing drift, validate exposure and pixel quality handling, design independent human-annotated reference sets, and add tracking after registration.
