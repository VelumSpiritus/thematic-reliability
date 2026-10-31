"""Thematic network analysis (after Attride-Stirling 2001).

Three levels: basic themes (from the codes), organizing themes (groups
of basic themes that share a conceptual thread), and global themes
(the overarching narratives the network resolves to).

The network is the structure that makes thematic analysis auditable.
Each global theme traces down through organizing themes to the basic
themes to the coded data. Drift at any level propagates upward — a
drifting code undermines the basic theme it feeds, which weakens the
organizing theme above it.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thematic_reliability.drift import DriftReport


@dataclass
class BasicTheme:
    """A theme derived directly from one or more codes in the data."""

    name: str
    codes: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class OrganizingTheme:
    """A cluster of basic themes sharing a conceptual thread."""

    name: str
    basic_themes: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class GlobalTheme:
    """An overarching narrative the network resolves to."""

    name: str
    organizing_themes: list[str] = field(default_factory=list)
    description: str = ""


class ThematicNetwork:
    """Three-level thematic network with traceability from global to code.

    Build the network bottom-up: define basic themes from your codes,
    group them into organizing themes, then name the global themes they
    support. The structure makes it possible to trace any global claim
    back through the organizing and basic levels to the coded data.
    """

    def __init__(self, name: str = ""):
        self.name = name
        self.basic: dict[str, BasicTheme] = {}
        self.organizing: dict[str, OrganizingTheme] = {}
        self.global_themes: dict[str, GlobalTheme] = {}

    def add_basic(self, theme: BasicTheme) -> None:
        self.basic[theme.name] = theme

    def add_organizing(self, theme: OrganizingTheme) -> None:
        self.organizing[theme.name] = theme

    def add_global(self, theme: GlobalTheme) -> None:
        self.global_themes[theme.name] = theme

    def codes_for_global(self, global_name: str) -> list[str]:
        """Trace a global theme down to the codes that support it."""
        gt = self.global_themes[global_name]
        codes = []
        for ot_name in gt.organizing_themes:
            ot = self.organizing[ot_name]
            for bt_name in ot.basic_themes:
                bt = self.basic[bt_name]
                codes.extend(bt.codes)
        return sorted(set(codes))

    def coverage(self, all_codes: list[str]) -> dict[str, list[str]]:
        """Which codes are covered by the network and which are not.

        Returns {"covered": [...], "uncovered": [...]}.
        """
        covered = set()
        for bt in self.basic.values():
            covered.update(bt.codes)
        uncovered = sorted(set(all_codes) - covered)
        return {"covered": sorted(covered), "uncovered": uncovered}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "basic_themes": [
                {"name": t.name, "codes": t.codes, "description": t.description}
                for t in self.basic.values()
            ],
            "organizing_themes": [
                {
                    "name": t.name,
                    "basic_themes": t.basic_themes,
                    "description": t.description,
                }
                for t in self.organizing.values()
            ],
            "global_themes": [
                {
                    "name": t.name,
                    "organizing_themes": t.organizing_themes,
                    "description": t.description,
                }
                for t in self.global_themes.values()
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ThematicNetwork:
        net = cls(name=d.get("name", ""))
        for bt in d.get("basic_themes", []):
            net.add_basic(BasicTheme(**bt))
        for ot in d.get("organizing_themes", []):
            net.add_organizing(OrganizingTheme(**ot))
        for gt in d.get("global_themes", []):
            net.add_global(GlobalTheme(**gt))
        return net


def drift_impact(
    network: ThematicNetwork,
    report: DriftReport,
    threshold: float = -0.1,
) -> list[dict]:
    """Identify which themes in a network are affected by drifting codes.

    Traces drifting codes upward through the network: basic themes that
    contain a drifting code, organizing themes that contain an affected
    basic theme, and global themes that contain an affected organizing theme.

    Returns a list of dicts with keys: level ("basic", "organizing", "global"),
    name, and drifting_codes (the codes causing the impact at that level).
    """
    drifting = {code for code, _ in report.drifting_codes(threshold)}
    if not drifting:
        return []

    results = []
    affected_basic = set()
    for bt in network.basic.values():
        hit = drifting & set(bt.codes)
        if hit:
            affected_basic.add(bt.name)
            results.append({
                "level": "basic",
                "name": bt.name,
                "drifting_codes": sorted(hit),
            })

    affected_organizing = set()
    for ot in network.organizing.values():
        hit_basics = affected_basic & set(ot.basic_themes)
        if hit_basics:
            affected_organizing.add(ot.name)
            codes = set()
            for bn in hit_basics:
                codes |= drifting & set(network.basic[bn].codes)
            results.append({
                "level": "organizing",
                "name": ot.name,
                "drifting_codes": sorted(codes),
            })

    for gt in network.global_themes.values():
        hit_orgs = affected_organizing & set(gt.organizing_themes)
        if hit_orgs:
            codes = set()
            for on in hit_orgs:
                ot = network.organizing[on]
                for bn in set(ot.basic_themes) & affected_basic:
                    codes |= drifting & set(network.basic[bn].codes)
            results.append({
                "level": "global",
                "name": gt.name,
                "drifting_codes": sorted(codes),
            })

    return results
