"""Coding drift on matched calibration units, with bidirectional category diagnostics."""
from __future__ import annotations
from dataclasses import dataclass, field
from thematic_reliability.agreement import cohen_kappa


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _slope(points):
    if len(points) < 2:
        return None
    x_bar = sum(x for x, _ in points) / len(points)
    y_bar = sum(y for _, y in points) / len(points)
    denominator = sum((x - x_bar) ** 2 for x, _ in points)
    return sum((x - x_bar) * (y - y_bar) for x, y in points) / denominator if denominator else 0.0


@dataclass(frozen=True)
class CodeAgreement:
    """One-vs-rest counts on paired units; baseline is a reference, not truth."""
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def baseline_count(self):
        return self.true_positive + self.false_negative

    @property
    def recoding_count(self):
        return self.true_positive + self.false_positive

    @property
    def precision(self):
        return _ratio(self.true_positive, self.recoding_count)

    @property
    def recall(self):
        return _ratio(self.true_positive, self.baseline_count)

    @property
    def agreement(self):
        """Symmetric positive-specific agreement: 2TP / (2TP + FP + FN)."""
        return _ratio(2 * self.true_positive, 2 * self.true_positive + self.false_positive + self.false_negative)

    @property
    def overuse_rate(self):
        """Fraction of baseline other-code units recoded as this code."""
        return _ratio(self.false_positive, self.false_positive + self.true_negative)

    @property
    def omission_rate(self):
        """Fraction of baseline this-code units recoded as another code."""
        return _ratio(self.false_negative, self.baseline_count)

    @property
    def prevalence_delta(self):
        n = self.true_positive + self.false_positive + self.false_negative + self.true_negative
        return _ratio(self.recoding_count - self.baseline_count, n)


def _per_code_metrics(baseline, recoding, categories):
    if len(baseline) != len(recoding):
        raise ValueError("paired coding sequences must have equal lengths")
    result = {}
    for code in categories:
        tp = fp = fn = tn = 0
        for base, current in zip(baseline, recoding):
            if base == code and current == code: tp += 1
            elif current == code: fp += 1
            elif base == code: fn += 1
            else: tn += 1
        result[code] = CodeAgreement(tp, fp, fn, tn)
    return result


def _per_code_agreement(baseline, recoding, categories):
    """Symmetric positive-specific agreement; None when neither coding uses a code."""
    return {code: value.agreement for code, value in _per_code_metrics(baseline, recoding, categories).items()}


@dataclass
class DriftWindow:
    window_index: int
    kappa: float
    p_observed: float
    p_expected: float
    n_units: int
    per_code: dict[str, float | None] = field(default_factory=dict)
    per_code_metrics: dict[str, CodeAgreement] = field(default_factory=dict)
    unit_ids: tuple = ()


@dataclass
class DriftReport:
    windows: list[DriftWindow]
    categories: list[str]
    common_units: tuple = ()
    comparison_metrics: list[dict[str, CodeAgreement]] | None = None

    @property
    def kappas(self) -> list[float]:
        return [w.kappa for w in self.windows]

    @property
    def trend(self) -> float | None:
        """Slope of kappa over window index (least-squares). Negative = drift."""
        n = len(self.windows)
        if n < 2:
            return None
        xs = list(range(n))
        ys = self.kappas
        x_bar = sum(xs) / n
        y_bar = sum(ys) / n
        num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
        den = sum((x - x_bar) ** 2 for x in xs)
        if den == 0:
            return 0.0
        return num / den

    def per_code_trends(self):
        """Slopes per original round index on the common calibration panel.

        Per-window descriptive scores still use each window's paired units.
        Undefined denominators supply no observation to a metric's slope.
        """
        result = {}
        for code in self.categories:
            trends = {}
            for name in ("agreement", "precision", "recall", "overuse_rate", "omission_rate", "prevalence_delta"):
                points = []
                for index, window in enumerate(self.windows):
                    metrics = self.comparison_metrics[index] if self.comparison_metrics is not None else window.per_code_metrics
                    value = getattr(metrics[code], name) if code in metrics else (window.per_code.get(code) if name == "agreement" and self.comparison_metrics is None else None)
                    if value is not None:
                        points.append((window.window_index, value))
                trends[name] = _slope(points)
            result[code] = trends
        return result

    def drifting_codes(self, threshold: float = -0.1) -> list[tuple[str, float]]:
        """Flag falling positive agreement or rising overuse/omission.

        Returns (code, worst_directional_slope), ascending. A rising error
        rate is negated so a negative score consistently means deterioration.
        This diagnostic is neither kappa nor a test of statistical significance.
        """
        results = []
        for code, trends in self.per_code_trends().items():
            slopes = [trends["agreement"]]
            slopes += [-trends[name] if trends[name] is not None else None for name in ("overuse_rate", "omission_rate")]
            defined = [value for value in slopes if value is not None]
            if defined and min(defined) < threshold:
                results.append((code, min(defined)))
        return sorted(results, key=lambda item: item[1])

    def summary(self) -> str:
        lines = ["Drift report: %d windows, %d categories" % (len(self.windows), len(self.categories))]
        for window in self.windows:
            lines.append("  window %d: kappa=%.4f  agreement=%.1f%%  n=%d" % (window.window_index, window.kappa, window.p_observed * 100, window.n_units))
        trend = self.trend
        if trend is not None:
            lines.append("  overall kappa trend: %.4f" % trend)
        if self.comparison_metrics is not None:
            lines.append("  per-code trend panel: %d units common to reported windows" % len(self.common_units))
            if not self.common_units:
                lines.append("  per-code trends unavailable: no common calibration units")
        if len({window.unit_ids for window in self.windows}) > 1:
            lines.append("  calibration subsets vary; overall kappa windows use different samples")
        drifting = self.drifting_codes()
        if drifting:
            lines.append("  drifting codes (worst directional slope):")
            for code, slope in drifting:
                lines.append("    %s: %.4f" % (code, slope))
        return "\n".join(lines)


def measure_drift(baseline_codings: dict, recodings: list[dict], categories: list | None = None) -> DriftReport:
    """Describe each paired window and compare code trends on a common panel.

    Window kappa/observed/expected agreement use the same paired units and
    calculations as before. Per-code positive agreement is symmetric; precision,
    recall, overuse and omission diagnostics retain their own denominators.
    Trend comparisons use only baseline units present in every eligible round.
    Windows with fewer than two paired units are omitted, preserving their
    original round indices in the remaining per-code trends.
    """
    if categories is None:
        labels = set(baseline_codings.values())
        for recoding in recodings:
            labels.update(recoding.values())
        categories = sorted(labels)
    else:
        categories = list(categories)
    if len(set(categories)) != len(categories):
        raise ValueError("categories must be unique")
    windows, rounds = [], []
    for index, recoding in enumerate(recodings):
        shared = sorted(set(baseline_codings) & set(recoding))
        if len(shared) < 2:
            continue
        base = [baseline_codings[unit] for unit in shared]
        current = [recoding[unit] for unit in shared]
        if (set(base) | set(current)) - set(categories):
            raise ValueError("categories must include every label on paired calibration units")
        kappa, observed, expected = cohen_kappa(base, current, categories)
        metrics = _per_code_metrics(base, current, categories)
        windows.append(DriftWindow(index, kappa, observed, expected, len(shared), {code: value.agreement for code, value in metrics.items()}, metrics, tuple(shared)))
        rounds.append(recoding)
    common = set(windows[0].unit_ids) if windows else set()
    for window in windows[1:]:
        common.intersection_update(window.unit_ids)
    common_units = tuple(sorted(common))
    comparisons = [_per_code_metrics([baseline_codings[u] for u in common_units], [recoding[u] for u in common_units], categories) for recoding in rounds]
    return DriftReport(windows, categories, common_units, comparisons)
