"""Coding drift detection over sequential windows.

The core problem: a coder's application of codes shifts as they encounter
more data. The codebook stays the same, but the coder's interpretation
drifts — sometimes toward sharper distinctions the codebook doesn't capture,
sometimes toward conflation of codes that should stay separate.

Drift is measurable. Code a calibration set at the start. Re-code it
(or a subset) at intervals. Kappa between the original calibration coding
and each re-coding measures drift from your own baseline. A declining
kappa means the coder's practice is moving away from the codebook.

Per-code drift tells you WHERE it's happening: which codes are being
applied more or less consistently over time.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from thematic_reliability.agreement import cohen_kappa


@dataclass
class DriftWindow:
    """One measurement window in a drift analysis."""

    window_index: int
    kappa: float
    p_observed: float
    p_expected: float
    n_units: int
    per_code: dict[str, float] = field(default_factory=dict)


@dataclass
class DriftReport:
    """Results of a drift analysis across sequential coding windows."""

    windows: list[DriftWindow]
    categories: list[str]

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

    def drifting_codes(self, threshold: float = -0.1) -> list[tuple[str, float]]:
        """Codes whose per-code agreement trend is below threshold.

        Returns (code_name, slope) pairs sorted by slope ascending (worst first).
        """
        if len(self.windows) < 2:
            return []

        results = []
        for code in self.categories:
            values = [w.per_code.get(code, 0.0) for w in self.windows]
            n = len(values)
            xs = list(range(n))
            x_bar = sum(xs) / n
            y_bar = sum(values) / n
            num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, values))
            den = sum((x - x_bar) ** 2 for x in xs)
            slope = num / den if den else 0.0
            if slope < threshold:
                results.append((code, slope))

        return sorted(results, key=lambda t: t[1])

    def summary(self) -> str:
        lines = ["Drift report: %d windows, %d categories" % (len(self.windows), len(self.categories))]
        for w in self.windows:
            lines.append(
                "  window %d: kappa=%.4f  agreement=%.1f%%  n=%d"
                % (w.window_index, w.kappa, w.p_observed * 100, w.n_units)
            )
        trend = self.trend
        if trend is not None:
            direction = "stable" if abs(trend) < 0.01 else ("declining" if trend < 0 else "improving")
            lines.append("  trend: %.4f (%s)" % (trend, direction))
        drifters = self.drifting_codes()
        if drifters:
            lines.append("  drifting codes:")
            for code, slope in drifters:
                lines.append("    %s: slope=%.4f" % (code, slope))
        return "\n".join(lines)


def _per_code_agreement(
    baseline: list, recoding: list, categories: list
) -> dict[str, float]:
    """Per-code specific agreement (proportion of units with that code
    in the baseline that received the same code in the recoding)."""
    result = {}
    for code in categories:
        matches = 0
        total = 0
        for b, r in zip(baseline, recoding):
            if b == code:
                total += 1
                if r == code:
                    matches += 1
        result[code] = matches / total if total > 0 else 1.0
    return result


def measure_drift(
    baseline_codings: dict,
    recodings: list[dict],
    categories: list | None = None,
) -> DriftReport:
    """Measure coding drift across sequential re-coding rounds.

    Parameters
    ----------
    baseline_codings : dict
        {unit_id: code} from the initial calibration coding.
    recodings : list of dicts
        Each dict is {unit_id: code} from a re-coding round, in chronological
        order. Only units present in both baseline and the re-coding are compared.
    categories : list, optional
        Explicit category set. Inferred from all data when omitted.

    Returns
    -------
    DriftReport
        Kappa per window, per-code agreement trends, overall trend.
    """
    if categories is None:
        all_labels = set(baseline_codings.values())
        for rc in recodings:
            all_labels |= set(rc.values())
        categories = sorted(all_labels)

    windows = []
    for i, recoding in enumerate(recodings):
        shared = sorted(set(baseline_codings) & set(recoding))
        if len(shared) < 2:
            continue

        base_seq = [baseline_codings[uid] for uid in shared]
        recode_seq = [recoding[uid] for uid in shared]

        kappa, p_obs, p_exp = cohen_kappa(base_seq, recode_seq, categories)
        per_code = _per_code_agreement(base_seq, recode_seq, categories)

        windows.append(
            DriftWindow(
                window_index=i,
                kappa=kappa,
                p_observed=p_obs,
                p_expected=p_exp,
                n_units=len(shared),
                per_code=per_code,
            )
        )

    return DriftReport(windows=windows, categories=categories)
