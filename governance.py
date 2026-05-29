"""Constitution, proposals, and voting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import MAX_ACTIVE_PROPOSALS, PASS_THRESHOLD, VOTE_QUORUM


@dataclass
class Proposal:
    id: int
    proposer: str
    amendment: str
    created_turn: int
    closes_turn: int
    yes_votes: int = 0
    no_votes: int = 0
    status: str = "open"
    voters: Dict[str, str] = field(default_factory=dict)


@dataclass
class GovernanceState:
    constitution_text: str
    version: int
    proposals: List[Proposal] = field(default_factory=list)
    next_proposal_id: int = 1
    amendments_passed: int = 0
    amendments_rejected: int = 0

    def open_proposals(self, turn: int) -> List[Proposal]:
        return [p for p in self.proposals if p.status == "open" and turn <= p.closes_turn]

    def has_open_proposals(self, turn: int) -> bool:
        return len(self.open_proposals(turn)) > 0

    def create_proposal(
        self, proposer: str, amendment: str, turn: int, duration: int = 24
    ) -> Optional[Proposal]:
        open_count = sum(1 for p in self.proposals if p.status == "open")
        if open_count >= MAX_ACTIVE_PROPOSALS:
            return None
        p = Proposal(
            id=self.next_proposal_id,
            proposer=proposer,
            amendment=amendment,
            created_turn=turn,
            closes_turn=turn + duration,
        )
        self.next_proposal_id += 1
        self.proposals.append(p)
        return p

    def cast_vote(
        self, proposal_id: int, voter: str, vote: str, turn: int, alive_count: int
    ) -> Optional[str]:
        vote = vote.lower()
        if vote not in ("yes", "no"):
            return "invalid vote"
        for p in self.proposals:
            if p.id != proposal_id:
                continue
            if p.status != "open" or turn > p.closes_turn:
                return "proposal closed"
            if voter in p.voters:
                return "already voted"
            p.voters[voter] = vote
            if vote == "yes":
                p.yes_votes += 1
            else:
                p.no_votes += 1
            return None
        return "proposal not found"

    def close_due_proposals(self, turn: int, alive_count: int) -> List[str]:
        messages: List[str] = []
        for p in self.proposals:
            if p.status != "open" or turn < p.closes_turn:
                continue
            total_votes = p.yes_votes + p.no_votes
            quorum = total_votes / max(1, alive_count)
            if quorum < VOTE_QUORUM:
                p.status = "failed_quorum"
                self.amendments_rejected += 1
                messages.append(f"Proposal #{p.id} failed quorum ({quorum:.0%})")
                continue
            yes_ratio = p.yes_votes / max(1, total_votes)
            if yes_ratio >= PASS_THRESHOLD:
                p.status = "passed"
                self.constitution_text = (
                    self.constitution_text.rstrip() + f"\n[Amendment v{self.version + 1}] " + p.amendment
                )
                self.version += 1
                self.amendments_passed += 1
                messages.append(f"Proposal #{p.id} PASSED ({yes_ratio:.0%} yes)")
            else:
                p.status = "rejected"
                self.amendments_rejected += 1
                messages.append(f"Proposal #{p.id} rejected ({yes_ratio:.0%} yes)")
        return messages

    def stability_score(self) -> float:
        total = self.amendments_passed + self.amendments_rejected
        if total == 0:
            return 0.7
        pass_rate = self.amendments_passed / total
        # Moderate pass rate = stability
        return 1.0 - abs(pass_rate - 0.5) * 1.2
