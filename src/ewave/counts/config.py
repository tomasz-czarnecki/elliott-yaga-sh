"""The versioned rules file (rules/counts.yaml). Nothing in this package hard-codes a threshold or a Fib number."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..ingest.config import project_root


def rules_path() -> Path:
    return project_root() / "rules" / "counts.yaml"


@dataclass(frozen=True)
class Config:
    raw: dict
    digest: str

    @property
    def version(self) -> str:
        return self.raw["version"]

    @property
    def tree(self) -> dict:
        return self.raw["tree"]

    @property
    def root(self) -> dict:
        return self.raw["root"]

    @property
    def frames(self) -> dict:
        return self.raw["frames"]

    @property
    def odds(self) -> dict:
        return self.raw["odds"]

    @property
    def pivots(self) -> dict:
        return self.raw["pivots"]

    @property
    def rules(self) -> dict:
        return self.raw["rules"]

    @property
    def grammar(self) -> dict:
        return self.raw["grammar"]

    @property
    def inside(self) -> dict:
        return self.raw["inside"]

    @property
    def levels(self) -> dict:
        return self.raw["levels"]

    @property
    def time(self) -> dict:
        return self.raw["time"]

    @property
    def fit(self) -> dict:
        return self.raw["fit"]

    def replaced(self, **sections) -> "Config":
        """A copy with whole top-level sections merged over; for tests."""
        raw = {**self.raw}
        for key, value in sections.items():
            raw[key] = {**raw[key], **value}
        return Config(raw, hashlib.sha256(yaml.safe_dump(raw, sort_keys=True).encode()).hexdigest()[:12])


def load_config(path: Path | str | None = None) -> Config:
    p = Path(path) if path else rules_path()
    data = p.read_bytes()
    return Config(yaml.safe_load(data), hashlib.sha256(data).hexdigest()[:12])
