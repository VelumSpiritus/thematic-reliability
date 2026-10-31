"""Codebook and code definitions for thematic analysis.

A codebook is the shared reference that all coding is measured against.
Each code has a name, a definition, and inclusion/exclusion criteria.
The codebook is what makes reliability measurable: two coders can only
agree or disagree relative to a codebook that defines what each code means.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json


@dataclass
class Code:
    """One code in a codebook."""

    name: str
    definition: str
    inclusion: str = ""
    exclusion: str = ""
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"name": self.name, "definition": self.definition}
        if self.inclusion:
            d["inclusion"] = self.inclusion
        if self.exclusion:
            d["exclusion"] = self.exclusion
        if self.examples:
            d["examples"] = self.examples
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Code:
        return cls(
            name=d["name"],
            definition=d["definition"],
            inclusion=d.get("inclusion", ""),
            exclusion=d.get("exclusion", ""),
            examples=d.get("examples", []),
        )


class Codebook:
    """A structured set of codes with their definitions.

    The codebook is the instrument. Its reliability is measured by how
    consistently two coders apply it to the same material — that consistency
    is what Cohen's kappa and Krippendorff's alpha measure.
    """

    def __init__(self, name: str = "", description: str = ""):
        self.name = name
        self.description = description
        self.codes: dict[str, Code] = {}

    def add(self, code: Code) -> None:
        self.codes[code.name] = code

    def remove(self, name: str) -> Code:
        return self.codes.pop(name)

    def categories(self) -> list[str]:
        return sorted(self.codes.keys())

    def __len__(self) -> int:
        return len(self.codes)

    def __contains__(self, name: str) -> bool:
        return name in self.codes

    def __getitem__(self, name: str) -> Code:
        return self.codes[name]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "codes": [c.to_dict() for c in self.codes.values()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Codebook:
        cb = cls(name=d.get("name", ""), description=d.get("description", ""))
        for cd in d.get("codes", []):
            cb.add(Code.from_dict(cd))
        return cb

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> Codebook:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
