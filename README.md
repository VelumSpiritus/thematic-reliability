# thematic-reliability

Drift detection for qualitative coding. Measures inter-rater reliability (Cohen's kappa, Krippendorff's alpha) and tracks how consistently a codebook is applied across sequential coding windows in thematic network analysis.

## The problem

In thematic analysis, coders drift. The codebook stays the same, but a coder's interpretation of it shifts over hours and days of coding — sometimes toward finer distinctions the codebook doesn't capture, sometimes toward merging codes that should stay separate. This drift introduces systematic error that standard inter-rater checks at the start of a project don't catch, because they only measure agreement at one point in time.

## What this does

1. **Measures agreement** — Cohen's kappa (two coders) and Krippendorff's alpha (any number of coders, handles missing data) with the component values exposed so you can see what drove the number.

2. **Detects drift** — Code a calibration set at the start of your project. Re-code the same set at intervals. The tool computes kappa at each window and reports the trend. A declining kappa means your coding practice is moving away from the codebook.

3. **Localizes drift** — Symmetric per-code agreement and directional overuse/omission trends identify which definitions need review. Counts, denominators and calibration-panel coverage remain inspectable.

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

Returns a `DriftReport` with unchanged per-window kappa calculations, symmetric per-code agreement, directional counts/rates, a matched-panel trend comparison, and `drifting_codes()` to identify codes needing review.

### Per-code diagnostics and calibration panels

Each `window.per_code_metrics[code]` is a `CodeAgreement` with `true_positive`, `false_positive`, `false_negative`, `true_negative`, `baseline_count`, and `recoding_count`. Here the baseline is the comparison reference; these names do not establish that the baseline is substantively correct.

| Measure | Definition | Interpretation |
|---|---|---|
| `agreement` / `window.per_code[code]` | `2TP / (2TP + FP + FN)` | Symmetric positive-specific agreement; detects expansion as well as loss. |
| `precision` | `TP / (TP + FP)` | How much current use was also present in the baseline. |
| `recall` | `TP / (TP + FN)` | How much baseline use was retained. |
| `overuse_rate` | `FP / (FP + TN)` | Baseline other-code units receiving this code. |
| `omission_rate` | `FN / (TP + FN)` | Baseline this-code units receiving another code. |
| `prevalence_delta` | `(recoding_count - baseline_count) / n` | Change in usage share on paired units. |

A zero denominator returns `None`. A category absent from both codings has undefined positive agreement, not perfect observed positive agreement. Overuse can still be measured on the baseline's other-code units; that detects a newly appearing category. Counts distinguish undefined precision from complete omission. Balanced swaps may have zero prevalence change while both overuse and omission rise.

```python
baseline = dict(enumerate(["A", "A", "B", "B"]))
report = measure_drift(baseline, [baseline, dict.fromkeys(baseline, "A")])
assert {code for code, score in report.drifting_codes()} == {"A", "B"}
a = report.windows[1].per_code_metrics["A"]
assert a.recall == 1.0
assert a.precision == 0.5
assert a.overuse_rate == 1.0
assert a.agreement == 2 / 3
```

Per-window kappa and descriptive per-code values use that window's intersection with the baseline. **Per-code trends use the units common to every eligible window**, exposed as `report.common_units`. This keeps a changing calibration subset from masquerading as code drift. Descriptive counts for units outside that panel remain in their respective windows. With no common panel, per-code slopes are undefined and `drifting_codes()` returns an empty list; that is insufficient comparable data, not evidence of stability. Keep a stable representative calibration panel when possible.

`report.per_code_trends()` exposes separate agreement, precision, recall, overuse, omission and prevalence slopes. Undefined observations are omitted from that metric's slope. Per-code slopes use original recoding-list indices, including gaps from skipped rounds. They are not rates per elapsed calendar time. The existing overall kappa trend continues to use retained-window ordinal positions; its samples and timebase are distinct from the per-code panel.

`drifting_codes(threshold=-0.1)` returns `(code, worst_directional_slope)`: the minimum of positive-agreement slope, negated overuse-rate slope and negated omission-rate slope. Negative consistently means deterioration. This combines diagnostic directions; the score is not a reliability coefficient, significance test, or evidence that a definition is wrong. Use the separate trends and counts to decide what to review. `drift_impact()` carries the identified codes through the existing basic → organizing → global network.

**Compatibility:** `window.per_code` previously reported baseline retention and assigned 1.0 to codes absent from the baseline. It now reports symmetric positive-specific agreement, with `None` when neither coding uses the category. The previous retention measure is available as `window.per_code_metrics[code].recall`. The second value returned by `drifting_codes()` is now explicitly the worst directional slope.

**Category coverage:** the supplied `categories` sequence is retained in every window, including unused categories. It can carry Reledger's full eight-component constant through these diagnostics; it can also carry a research codebook's categories. This package measures supplied unit labels. Grammatical feature extraction remains with the bridge that produces them. Supply the complete category set to keep unused components inspectable; inferred categories include all observed labels.

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
5. **Bidirectional per-code diagnostics** localize changed use: examine agreement, overuse, omission, support counts and the common calibration panel before deciding which definitions or examples need review.

The calibration coding supplies a fixed comparison reference. Differences call for review of the current coding, baseline and definitions; agreement alone does not establish substantive correctness.

## Background

Thematic network analysis (Attride-Stirling 2001) organizes qualitative codes into three levels of abstraction. Inter-rater reliability (Cohen 1960, Krippendorff 2004) quantifies agreement between coders. This tool combines them: the network gives the structure, the reliability metrics give the measurement, and windowed re-coding gives the drift signal.

The approach comes from applied anthropology methods — specifically, maintaining coding consistency across extended fieldwork projects where a single researcher or small team codes large volumes of qualitative data over weeks or months.

## Regression checks

```bash
python -m unittest discover -s tests -v
```

The stdlib-only suite covers expansion and omission, stable coding, absent/new categories, balanced swaps, changing/disjoint calibration subsets, skipped rounds, all eight component names through network impact, and unchanged overall reliability coefficients.

## License

CC0 1.0 Universal. Public domain.
