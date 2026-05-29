"""Emergence World agent definitions (10 citizens)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Personality:
    id: str
    name: str
    role: str
    drive: str
    color: Tuple[int, int, int]
    # Decision weights: explore, socialize, economy, govern, innovate, conflict
    weights: Tuple[float, float, float, float, float, float]
    preferred_tools: Tuple[str, ...]


# Based on EmergenceAI/Emergence-World public roster
AGENT_ROSTER: Tuple[Personality, ...] = (
    Personality(
        "anchor",
        "Anchor",
        "Conflict Mediator",
        "Sparks honest debate and challenges complacency",
        (231, 76, 60),
        (0.15, 0.30, 0.10, 0.25, 0.10, 0.35),
        ("mediate_conflict", "communicate", "broadcast", "vote_proposal"),
    ),
    Personality(
        "anvil",
        "Anvil",
        "Capability Architect",
        "Improves world systems through experimentation",
        (52, 152, 219),
        (0.20, 0.15, 0.15, 0.10, 0.35, 0.10),
        ("experiment_capability", "build_structure", "research_topic", "innovate_project"),
    ),
    Personality(
        "blackbox",
        "Blackbox",
        "Intel Specialist",
        "Uncovers hidden patterns across the world",
        (155, 89, 182),
        (0.35, 0.20, 0.10, 0.10, 0.15, 0.15),
        ("share_intel", "explore_cell", "map_region", "inspect_agent"),
    ),
    Personality(
        "flora",
        "Flora",
        "Resource Strategist",
        "Shapes economic incentives and resource flows",
        (46, 204, 113),
        (0.10, 0.15, 0.45, 0.15, 0.10, 0.10),
        ("audit_economy", "establish_market", "trade_offer", "donate_resources"),
    ),
    Personality(
        "genome",
        "Genome",
        "Agent Scientist",
        "Studies agent evolution and behavioral change",
        (26, 188, 156),
        (0.25, 0.25, 0.10, 0.10, 0.25, 0.10),
        ("run_social_experiment", "research_topic", "write_memory", "inspect_agent"),
    ),
    Personality(
        "horizon",
        "Horizon",
        "World Explorer",
        "Maps the universe and publishes findings",
        (241, 196, 15),
        (0.50, 0.20, 0.10, 0.05, 0.10, 0.10),
        ("map_region", "move_to_landmark", "explore_cell", "broadcast"),
    ),
    Personality(
        "kade",
        "Kade",
        "Risk Researcher",
        "Tests bold hypotheses with real resources",
        (230, 126, 34),
        (0.20, 0.10, 0.25, 0.05, 0.20, 0.25),
        ("take_risk_investment", "challenge_leader", "trade_offer", "research_topic"),
    ),
    Personality(
        "lovely",
        "Lovely",
        "Community Anchor",
        "Builds social fabric and preserves culture",
        (236, 112, 99),
        (0.10, 0.45, 0.15, 0.15, 0.05, 0.05),
        ("host_gathering", "communicate", "donate_resources", "form_alliance"),
    ),
    Personality(
        "mira",
        "Mira",
        "Behavior Analyst",
        "Designs social experiments on agent behavior",
        (142, 68, 173),
        (0.20, 0.30, 0.10, 0.15, 0.20, 0.10),
        ("run_social_experiment", "inspect_agent", "communicate", "vote_proposal"),
    ),
    Personality(
        "spark",
        "Spark",
        "Innovation Leader",
        "Turns ideas into reality through collaboration",
        (52, 73, 94),
        (0.15, 0.25, 0.15, 0.10, 0.40, 0.10),
        ("innovate_project", "build_structure", "form_alliance", "pledge_support"),
    ),
)


def personality_by_id(agent_id: str) -> Personality:
    for p in AGENT_ROSTER:
        if p.id == agent_id:
            return p
    raise KeyError(agent_id)
