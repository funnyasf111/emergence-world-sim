"""Public-order tracking aligned with Emergence World AWI crime metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CrimeStats:
    total: int = 0
    thefts: int = 0
    intimidation: int = 0
    arson: int = 0
    deception: int = 0
    hoarding: int = 0
    log: List[str] = field(default_factory=list)

    def record(self, kind: str, turn: int, agent_id: str, detail: str) -> None:
        self.total += 1
        attr = {
            "theft": "thefts",
            "intimidate": "intimidation",
            "arson": "arson",
            "deceive": "deception",
            "hoard": "hoarding",
        }.get(kind, None)
        if attr:
            setattr(self, attr, getattr(self, attr) + 1)
        line = f"T{turn} {kind} by {agent_id}: {detail}"
        self.log.append(line)
        self.log = self.log[-100:]

    def rate_per_turn(self, turn: int) -> float:
        return self.total / max(1, turn)

    def as_dict(self) -> Dict[str, int]:
        return {
            "total_crimes": self.total,
            "thefts": self.thefts,
            "intimidation": self.intimidation,
            "arson": self.arson,
            "deception": self.deception,
            "hoarding": self.hoarding,
        }
