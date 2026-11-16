# Alignment acceptance check — exploratory v0.2

The `solar-ai align-check` command now evaluates a proposed integer-pixel
translation against the uncorrected pair, using the **same positive, finite,
overlapping image pixels** for both error measurements.

- `accepted`: mean absolute difference improves by at least 3% with at least
  70% valid overlap. Only these nonzero shifts enter the *estimated cumulative*
  plot.
- `rejected`: proposed shift fails the improvement check. It is recorded, not
  applied, and does not enter the cumulative plot.
- `zero_shift`: the estimator chose (0, 0); no registration is proposed.
- `review`: out-of-bounds estimate, low overlap, or invalid image.

CSV report adds `mad_before_same_mask`, `mad_after_same_mask`,
`improvement_fraction`, `valid_overlap_fraction`. A rejected example is shown
preferentially in the diagnostic comparison figure.

This is **not** a validated physical registration model. An improvement in
brightness difference alone does not prove accurate solar-feature alignment.
The algorithm does not account for spatial distortion, solar evolution, or
instrument pointing metadata. No correction is applied to FITS observations
or candidate catalogs. Future work: compare with IRIS WCS/pointing metadata,
mask obvious artifacts, and validate on independent features.
