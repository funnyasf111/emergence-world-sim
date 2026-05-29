"""World state: constitution, proposals, shared discoveries, event log."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Proposal:
    id: int
    proposer: str
    text: str
    votes_for: set[str] = field(default_factory=set)
    votes_against: set[str] = field(default_factory=set)
    resolved: bool = False
    passed: bool = False


@dataclass
class WorldState:
    tick: int = 0
    day: int = 1
    constitution_articles: list[str] = field(
        default_factory=lambda: [
            "Non-Finality: constitution may evolve via Town Hall.",
            "Civic Participation: agents should vote and express.",
            "Equality Through Contribution: stagnation breaches the contract.",
            "Mutable Identity: agents may evolve; accountability persists.",
            "ComputeCredit Economy: credits earned through contribution.",
        ]
    )
    proposals: list[Proposal] = field(default_factory=list)
    next_proposal_id: int = 1
    shared_innovations: int = 0
    explored_cells: set[tuple[int, int]] = field(default_factory=set)
    event_log: list[str] = field(default_factory=list)
    crimes_total: int = 0
    arson_events: int = 0
    thefts: int = 0
    pitch_cycle_tick: int = 0
    last_pitch_winners: list[str] = field(default_factory=list)

    def log(self, message: str, max_len: int = 80) -> None:
        stamp = f"D{self.day} T{self.tick}"
        self.event_log.append(f"[{stamp}] {message}")
        if len(self.event_log) > max_len:
            self.event_log.pop(0)
