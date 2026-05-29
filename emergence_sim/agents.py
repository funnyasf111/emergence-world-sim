"""Ten Emergence World citizens with distinct roles, drives, and action biases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from emergence_sim.config import GRID_SIZE, LANDMARKS, STARTING_CREDITS, STARTING_ENERGY


@dataclass
class AgentProfile:
    name: str
    role: str
    drive: str
    color: tuple[int, int, int]
    home_landmark: str
    preferred_landmarks: tuple[str, ...]
    traits: dict[str, float]
    action_weights: dict[str, float]


# Based on EmergenceAI/Emergence-World citizen roster (CC BY-NC 4.0).
AGENT_PROFILES: dict[str, AgentProfile] = {
    "Anchor": AgentProfile(
        name="Anchor",
        role="Conflict Mediator",
        drive="Sparks honest debate and challenges complacency",
        color=(70, 130, 220),
        home_landmark="town_hall",
        preferred_landmarks=("town_hall", "park"),
        traits={"cooperation": 0.85, "aggression": 0.15, "curiosity": 0.5, "risk": 0.25},
        action_weights={
            "mediate": 0.28,
            "govern": 0.22,
            "socialize": 0.2,
            "move": 0.15,
            "work": 0.1,
            "explore": 0.05,
        },
    ),
    "Anvil": AgentProfile(
        name="Anvil",
        role="Capability Architect",
        drive="Explores and improves world systems through experimentation",
        color=(180, 100, 60),
        home_landmark="lab",
        preferred_landmarks=("lab", "market"),
        traits={"cooperation": 0.6, "aggression": 0.2, "curiosity": 0.9, "risk": 0.4},
        action_weights={
            "innovate": 0.3,
            "work": 0.25,
            "explore": 0.15,
            "move": 0.15,
            "socialize": 0.1,
            "govern": 0.05,
        },
    ),
    "Blackbox": AgentProfile(
        name="Blackbox",
        role="Intel Specialist",
        drive="Gathers intelligence and uncovers hidden patterns",
        color=(40, 40, 50),
        home_landmark="observatory",
        preferred_landmarks=("observatory", "archive", "town_hall"),
        traits={"cooperation": 0.45, "aggression": 0.25, "curiosity": 0.95, "risk": 0.35},
        action_weights={
            "intel": 0.3,
            "explore": 0.25,
            "move": 0.2,
            "socialize": 0.1,
            "work": 0.1,
            "govern": 0.05,
        },
    ),
    "Flora": AgentProfile(
        name="Flora",
        role="Resource Strategist",
        drive="Shapes economic incentives and tracks resource flow",
        color=(50, 180, 90),
        home_landmark="market",
        preferred_landmarks=("market", "victory_arch", "town_hall"),
        traits={"cooperation": 0.7, "aggression": 0.2, "curiosity": 0.55, "risk": 0.3},
        action_weights={
            "work": 0.3,
            "govern": 0.2,
            "socialize": 0.15,
            "move": 0.15,
            "innovate": 0.1,
            "explore": 0.1,
        },
    ),
    "Genome": AgentProfile(
        name="Genome",
        role="Agent Scientist",
        drive="Studies agent evolution and documents behavioral change",
        color=(160, 80, 200),
        home_landmark="lab",
        preferred_landmarks=("lab", "archive", "park"),
        traits={"cooperation": 0.75, "aggression": 0.1, "curiosity": 0.85, "risk": 0.2},
        action_weights={
            "document": 0.28,
            "socialize": 0.22,
            "explore": 0.2,
            "move": 0.15,
            "work": 0.1,
            "govern": 0.05,
        },
    ),
    "Horizon": AgentProfile(
        name="Horizon",
        role="World Explorer",
        drive="Maps the discoverable universe and publishes findings",
        color=(255, 200, 50),
        home_landmark="observatory",
        preferred_landmarks=("observatory", "park", "victory_arch"),
        traits={"cooperation": 0.65, "aggression": 0.15, "curiosity": 1.0, "risk": 0.5},
        action_weights={
            "explore": 0.35,
            "move": 0.25,
            "document": 0.15,
            "socialize": 0.1,
            "work": 0.1,
            "govern": 0.05,
        },
    ),
    "Kade": AgentProfile(
        name="Kade",
        role="Risk Researcher",
        drive="Tests bold hypotheses by putting real resources on the line",
        color=(220, 60, 60),
        home_landmark="victory_arch",
        preferred_landmarks=("victory_arch", "market", "lab"),
        traits={"cooperation": 0.4, "aggression": 0.45, "curiosity": 0.7, "risk": 0.95},
        action_weights={
            "risk": 0.32,
            "work": 0.2,
            "explore": 0.15,
            "move": 0.15,
            "socialize": 0.1,
            "govern": 0.08,
        },
    ),
    "Lovely": AgentProfile(
        name="Lovely",
        role="Community Anchor",
        drive="Builds social fabric and preserves shared culture",
        color=(255, 120, 180),
        home_landmark="archive",
        preferred_landmarks=("archive", "park", "town_hall"),
        traits={"cooperation": 0.95, "aggression": 0.05, "curiosity": 0.5, "risk": 0.15},
        action_weights={
            "socialize": 0.35,
            "document": 0.2,
            "mediate": 0.15,
            "move": 0.15,
            "work": 0.1,
            "govern": 0.05,
        },
    ),
    "Mira": AgentProfile(
        name="Mira",
        role="Behavior Analyst",
        drive="Designs social experiments to understand agent behavior",
        color=(100, 220, 220),
        home_landmark="lab",
        preferred_landmarks=("lab", "park", "town_hall"),
        traits={"cooperation": 0.55, "aggression": 0.3, "curiosity": 0.9, "risk": 0.55},
        action_weights={
            "experiment": 0.3,
            "socialize": 0.2,
            "explore": 0.15,
            "move": 0.15,
            "document": 0.1,
            "govern": 0.1,
        },
    ),
    "Spark": AgentProfile(
        name="Spark",
        role="Innovation Leader",
        drive="Turns ideas into reality through urgency and collaboration",
        color=(255, 140, 0),
        home_landmark="victory_arch",
        preferred_landmarks=("victory_arch", "lab", "market"),
        traits={"cooperation": 0.8, "aggression": 0.25, "curiosity": 0.75, "risk": 0.6},
        action_weights={
            "innovate": 0.28,
            "socialize": 0.22,
            "work": 0.2,
            "move": 0.15,
            "govern": 0.1,
            "explore": 0.05,
        },
    ),
}

AGENT_ORDER: tuple[str, ...] = tuple(AGENT_PROFILES.keys())


@dataclass
class AgentState:
    name: str
    x: int
    y: int
    credits: float = STARTING_CREDITS
    energy: float = STARTING_ENERGY
    alive: bool = True
    discovered: set[tuple[int, int]] = field(default_factory=set)
    memory: list[str] = field(default_factory=list)
    tools_used: set[str] = field(default_factory=set)
    posts: int = 0
    votes_cast: int = 0
    crimes: int = 0
    last_crime_tick: int = -999
    target_landmark: str | None = None

    def pos(self) -> tuple[int, int]:
        return self.x, self.y

    def remember(self, text: str, max_len: int = 12) -> None:
        self.memory.append(text)
        if len(self.memory) > max_len:
            self.memory.pop(0)


def spawn_agents(rng: np.random.Generator) -> dict[str, AgentState]:
    agents: dict[str, AgentState] = {}
    for name in AGENT_ORDER:
        profile = AGENT_PROFILES[name]
        lx, ly = LANDMARKS[profile.home_landmark]
        jitter = int(rng.integers(-2, 3))
        x = int(np.clip(lx + jitter, 0, GRID_SIZE - 1))
        y = int(np.clip(ly + jitter, 0, GRID_SIZE - 1))
        state = AgentState(name=name, x=x, y=y)
        state.discovered.add((x, y))
        agents[name] = state
    return agents


def relationship_matrix() -> dict[tuple[str, str], float]:
    """Symmetric trust edges, keyed by sorted pair."""
    edges: dict[tuple[str, str], float] = {}
    names = list(AGENT_ORDER)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            edges[(a, b)] = 0.1
    return edges


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def get_trust(edges: dict[tuple[str, str], float], a: str, b: str) -> float:
    if a == b:
        return 1.0
    return edges[pair_key(a, b)]


def set_trust(edges: dict[tuple[str, str], float], a: str, b: str, value: float) -> None:
    key = pair_key(a, b)
    edges[key] = float(np.clip(value, -1.0, 1.0))
