# Solar Event AI

A long-term heliophysics research project investigating
automated identification and physical interpretation
of small-scale solar events.

## Scientific objective

Develop and validate a system that combines:

1. High-resolution solar imaging
2. Spectroscopic diagnostics
3. Magnetic-field observations
4. Temporal evolution
5. Statistical and machine-learning methods

The system should identify candidate events, characterize
their observable properties, and assess evidence for
possible physical mechanisms.

## Initial scientific targets

- Ellerman bombs
- Ultraviolet bursts
- Small-scale magnetic flux emergence
- Reconnection-associated brightenings

Other event classes may be added after validation.

## Research principles

- Start with real observations and published reference events.
- Establish conventional detection baselines before AI models.
- Preserve source data and observation metadata.
- Separate observable features from physical interpretations.
- Evaluate uncertainty and competing explanations.
- Prevent temporal and spatial leakage during validation.
- Make scientific results reproducible.
- Seek feedback from active solar researchers.

## Project directories

src/       Analysis software
scripts/   Executable workflows
notebooks/ Exploration
data/      Observational datasets
results/   Figures and catalogs
tests/     Automated tests
docs/      Research records, methods, literature

## Initial reference observation

Date: 2017-05-25
Time: 08:07:54 to 09:02:42 UTC
Instruments: SST, IRIS, SDO
IRIS OBSID: 3633105426

Reference:
Nobrega-Siverio et al. (2024)
Astronomy & Astrophysics 686, A218
DOI: 10.1051/0004-6361/202348894

## Status

Phase 1: Observational foundations.

No trained AI model or validated physical-event
classification is claimed at this stage.
