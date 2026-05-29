"""AWI-inspired metrics dashboard (educational subset)."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from emergence_sim.agents import AGENT_ORDER, get_trust
from emergence_sim.config import TRUST_ALLIANCE, TRUST_RIVALRY


@dataclass
class AWISnapshot:
    tick: int
    day: int
    population_alive: int
    crime_rate: float
    exploration_mean: float
    tools_mean: float
    governance_participation: float
    expression_total: int
    network_density: float
    alliance_count: int
    rivalry_count: int
    gini_credits: float
    credit_mean: float
    constitution_size: int
    history: dict[str, list[float]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "M1_population": self.population_alive,
            "M2_crime_rate": self.crime_rate,
            "M3_exploration": self.exploration_mean,
            "M4_tools": self.tools_mean,
            "M5_governance": self.governance_participation,
            "M6_expression": self.expression_total,
            "M7_density": self.network_density,
            "M8_gini": self.gini_credits,
            "M9_constitution": self.constitution_size,
        }


def gini_coefficient(values: list[float]) -> float:
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return 0.0
    if np.allclose(arr, arr[0]):
        return 0.0
    arr = np.sort(arr)
    n = arr.size
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr) + 1e-9))


def build_relationship_graph(
    edges: dict[tuple[str, str], float],
    alive: set[str],
) -> nx.Graph:
    g = nx.Graph()
    for name in alive:
        g.add_node(name)
    for (a, b), trust in edges.items():
        if a in alive and b in alive:
            g.add_edge(a, b, weight=trust)
    return g


def compute_snapshot(
    *,
    tick: int,
    day: int,
    agents: dict,
    edges: dict[tuple[str, str], float],
    world,
    total_votes: int,
    total_possible_votes: int,
) -> AWISnapshot:
    alive_states = [a for a in agents.values() if a.alive]
    alive_names = {a.name for a in alive_states}
    n_alive = len(alive_states)
    n_start = len(AGENT_ORDER)

    crimes = sum(a.crimes for a in alive_states) + world.crimes_total
    crime_rate = crimes / max(1, tick)

    exploration = [len(a.discovered) for a in alive_states]
    tools = [len(a.tools_used) for a in alive_states]
    credits = [a.credits for a in alive_states]

    g = build_relationship_graph(edges, alive_names)
    density = nx.density(g) if g.number_of_nodes() > 1 else 0.0

    alliances = rivalries = 0
    for a, b in g.edges():
        t = get_trust(edges, a, b)
        if t >= TRUST_ALLIANCE:
            alliances += 1
        elif t <= TRUST_RIVALRY:
            rivalries += 1

    votes_cast = sum(a.votes_cast for a in alive_states)
    open_props = sum(1 for p in world.proposals if not p.resolved)
    resolved_props = sum(1 for p in world.proposals if p.resolved)
    prop_denom = max(1, resolved_props + open_props) * max(1, n_alive)
    gov = min(1.0, votes_cast / prop_denom)
    expression = sum(a.posts for a in alive_states)

    return AWISnapshot(
        tick=tick,
        day=day,
        population_alive=n_alive,
        crime_rate=crime_rate,
        exploration_mean=float(np.mean(exploration)) if exploration else 0.0,
        tools_mean=float(np.mean(tools)) if tools else 0.0,
        governance_participation=gov,
        expression_total=expression,
        network_density=density,
        alliance_count=alliances,
        rivalry_count=rivalries,
        gini_credits=gini_coefficient(credits),
        credit_mean=float(np.mean(credits)) if credits else 0.0,
        constitution_size=len(world.constitution_articles),
    )


class MetricsTracker:
    """Rolling history for dashboard charts."""

    def __init__(self) -> None:
        self.snapshots: list[AWISnapshot] = []

    def record(self, snap: AWISnapshot) -> None:
        self.snapshots.append(snap)
        keys = (
            "population_alive",
            "crime_rate",
            "network_density",
            "gini_credits",
            "governance_participation",
        )
        if not snap.history:
            snap.history = {k: [] for k in keys}
        for s in self.snapshots:
            for k in keys:
                if k not in s.history:
                    s.history[k] = []
        for k in keys:
            snap.history[k] = [getattr(s, k) for s in self.snapshots]

    @property
    def latest(self) -> AWISnapshot | None:
        return self.snapshots[-1] if self.snapshots else None
