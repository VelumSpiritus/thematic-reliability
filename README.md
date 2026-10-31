# thematic-reliability

Drift detection for qualitative coding. Measures inter-rater reliability (Cohen's kappa, Krippendorff's alpha) and tracks how consistently a codebook is applied across sequential coding windows in thematic network analysis.

## The problem

In thematic analysis, coders drift. The codebook stays the same, but a coder's interpretation of it shifts over hours and days of coding — sometimes toward finer distinctions the codebook doesn't capture, sometimes toward merging codes that should stay separate. This drift introduces systematic error that standard inter-rater checks at the start of a project don't catch, because they only measure agreement at one point in time.

## What this does

1. **Measures agreement** — Cohen's kappa (two coders) and Krippendorff's alpha (any number of coders, handles missing data) with the component values exposed so you can see what drove the number.

2. **Detects drift** — Code a calibration set at the start of your project. Re-code the same set at intervals. The tool computes kappa at each window and reports the trend. A declining kappa means your coding practice is moving away from the codebook.

3. **Localizes drift** — Per-code agreement trends tell you *which* codes are drifting, so you can re-read specific definitions rather than re-training on the entire codebook.

4. **Structures thematic networks** — Basic → organizing → global theme hierarchy (after Attride-Stirling 2001) with traceability from any global theme down to the codes and data that support it.

## Install

No dependencies. Python 3.10+ standard library only.

```
git clone https://github.com/VelumSpiritus/thematic-reliability.git
cd thematic-reliability
```

Use directly from the repo root.

## Quick start

```python
from thematic_reliability import cohen_kappa, measure_drift

# Two coders on the same 5 units
kappa, observed, expected = cohen_kappa(
    ["ACCESS", "TRUST", "WAIT", "ACCESS", "TRUST"],
    ["ACCESS", "TRUST", "ACCESS", "ACCESS", "TRUST"],
)
print(f"kappa={kappa:.3f}  agreement={observed:.0%}")

# Drift detection: baseline + re-codings over time
baseline = {"u1": "A", "u2": "B", "u3": "A", "u4": "B"}
recodings = [
    {"u1": "A", "u2": "B", "u3": "A", "u4": "B"},  # week 1: perfect
    {"u1": "A", "u2": "B", "u3": "B", "u4": "B"},  # week 3: one slip
    {"u1": "B", "u2": "A", "u3": "B", "u4": "A"},  # week 6: inverted
]
report = measure_drift(baseline, recodings)
print(report.summary())
```

## Demo

```
python -m thematic_reliability
```

Walks through a patient-experience coding scenario: defines a codebook, measures inter-rater reliability on a calibration set, detects drift across three re-coding rounds, identifies which codes are drifting, traces them through a thematic network, and reports which themes are affected.

## API

### `cohen_kappa(coder_a, coder_b, categories=None)`

Returns `(kappa, p_observed, p_expected)`. Two sequences of labels, same length, same unit order.

### `krippendorff_alpha(units, categories=None)`

Returns `(alpha, d_observed, d_expected)`. Takes a list of units where each unit is a list of labels from all coders who rated it. Handles missing data by omission (units with fewer than 2 labels are skipped).

### `percent_agreement(coder_a, coder_b)`

Simple observed agreement proportion.

### `measure_drift(baseline_codings, recodings, categories=None)`

Returns a `DriftReport` with per-window kappa, per-code agreement trends, overall trend slope, and `drifting_codes()` to identify which codes need attention.

### `Codebook` / `Code`

Structured codebook with names, definitions, inclusion/exclusion criteria, and examples. Serializes to/from JSON.

### `ThematicNetwork`

Three-level thematic network (basic → organizing → global). Traces any global theme down to its supporting codes. Reports which codes are covered by the network and which are not.

### `drift_impact(network, report, threshold=-0.1)`

Takes a `ThematicNetwork` and a `DriftReport` and traces drifting codes upward through the network hierarchy. Returns which basic, organizing, and global themes are affected by coding drift, and which specific codes are causing the impact at each level.

## Method

The drift detection approach:

1. At the start of a coding project, code a **calibration set** — a representative sample of units coded carefully against fresh codebook definitions.
2. At regular intervals during coding, **re-code the same calibration set** without looking at your previous answers.
3. Compute **Cohen's kappa between each re-coding and the original baseline**. This measures how far your current practice has moved from the codebook.
4. The **trend in kappa over time** is the drift signal. Stable or improving kappa means the codebook is being applied consistently. Declining kappa means the coder is drifting.
5. **Per-code agreement** localizes drift to specific codes, so remediation is targeted: re-read the definition, look at the inclusion/exclusion criteria, re-code a few examples.

This is the same logic as recalibrating an instrument: the calibration set is the known standard, and periodic measurement against it catches systematic error before it corrupts the dataset.

## Background

Thematic network analysis (Attride-Stirling 2001) organizes qualitative codes into three levels of abstraction. Inter-rater reliability (Cohen 1960, Krippendorff 2004) quantifies agreement between coders. This tool combines them: the network gives the structure, the reliability metrics give the measurement, and windowed re-coding gives the drift signal.

The approach comes from applied anthropology methods — specifically, maintaining coding consistency across extended fieldwork projects where a single researcher or small team codes large volumes of qualitative data over weeks or months.

## License

CC0 1.0 Universal. Public domain.
