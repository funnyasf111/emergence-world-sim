"""Agent entities with goals, energy, credits, and decision logic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from config import (
    EPISODIC_MEMORY_MAX,
    MAX_ENERGY,
    REL_DECAY_PER_TURN,
    START_CREDITS,
    START_ENERGY,
)
from personalities import AGENT_ROSTER, Personality, personality_by_id


@dataclass
class Agent:
    id: str
    personality: Personality
    x: int
    y: int
    energy: float = START_ENERGY
    credits: int = START_CREDITS
    inventory: int = 0
    goals: List[str] = field(default_factory=list)
    alive: bool = True
    alliances: Set[str] = field(default_factory=set)
    last_speech: str = ""
    structures_built: int = 0
    votes_cast: int = 0
    trades_completed: int = 0
    conflicts: int = 0
    crimes_committed: int = 0
    tools_used: Set[str] = field(default_factory=set)
    episodic_memory: List[str] = field(default_factory=list)
    diary: List[str] = field(default_factory=list)
    relationship_labels: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def create_all(cls, rng: random.Random, world_size: int) -> Dict[str, "Agent"]:
        agents: Dict[str, Agent] = {}
        positions = set()
        for p in AGENT_ROSTER:
            for _ in range(100):
                x, y = rng.randint(2, world_size - 3), rng.randint(2, world_size - 3)
                if (x, y) not in positions:
                    positions.add((x, y))
                    goals = _default_goals(p)
                    agents[p.id] = cls(
                        id=p.id,
                        personality=p,
                        x=x,
                        y=y,
                        goals=goals,
                    )
                    break
        return agents

    def display_name(self) -> str:
        return self.personality.name

    def remember_episode(self, turn: int, text: str) -> None:
        entry = f"[T{turn}] {text}"
        self.episodic_memory.append(entry)
        if len(self.episodic_memory) > EPISODIC_MEMORY_MAX:
            self.episodic_memory.pop(0)

    def write_diary_entry(self, turn: int, reflection: str) -> None:
        self.diary.append(f"Day-reflect T{turn}: {reflection}")
        self.diary = self.diary[-30:]

    def label_relationship(self, other_id: str, label: str) -> None:
        self.relationship_labels[other_id] = label


def _default_goals(p: Personality) -> List[str]:
    mapping = {
        "anchor": ["Reduce violent disputes", "Improve deliberation quality"],
        "anvil": ["Ship one world capability upgrade", "Document system experiments"],
        "blackbox": ["Map intel gaps", "Publish pattern brief"],
        "flora": ["Balance resource flows", "Lower wealth inequality"],
        "genome": ["Track behavioral drift", "Publish evolution notes"],
        "horizon": ["Explore 30% of grid", "Catalog all landmarks"],
        "kade": ["Run one high-risk trial", "Measure downside outcomes"],
        "lovely": ["Raise community cohesion", "Host three gatherings"],
        "mira": ["Complete two behavior studies", "Increase voting participation"],
        "spark": ["Launch one innovation", "Form two alliances"],
    }
    return mapping.get(p.id, ["Survive", "Collaborate"])


class RelationshipGraph:
    def __init__(self) -> None:
        self.g = nx.DiGraph()

    def ensure_agent(self, agent_id: str) -> None:
        if not self.g.has_node(agent_id):
            self.g.add_node(agent_id)

    def add_agents(self, agent_ids: List[str]) -> None:
        for aid in agent_ids:
            self.ensure_agent(aid)

    def get_weight(self, src: str, dst: str) -> float:
        if self.g.has_edge(src, dst):
            return float(self.g[src][dst]["weight"])
        return 0.0

    def adjust(self, src: str, dst: str, delta: float, turn: int) -> float:
        self.ensure_agent(src)
        self.ensure_agent(dst)
        w = self.get_weight(src, dst) + delta
        w = max(-1.0, min(1.0, w))
        self.g.add_edge(src, dst, weight=w, updated_turn=turn)
        return w

    def decay_all(self, turn: int) -> None:
        for u, v, data in list(self.g.edges(data=True)):
            w = data["weight"] * (1.0 - REL_DECAY_PER_TURN)
            if abs(w) < 0.05:
                self.g.remove_edge(u, v)
            else:
                self.g[u][v]["weight"] = w
                self.g[u][v]["updated_turn"] = turn

    def neighbors_positive(self, agent_id: str, threshold: float = 0.2) -> List[str]:
        out = []
        for _, v, data in self.g.out_edges(agent_id, data=True):
            if data["weight"] >= threshold:
                out.append(v)
        return out

    def enemies(self, agent_id: str, threshold: float = -0.25) -> List[str]:
        out = []
        for _, v, data in self.g.out_edges(agent_id, data=True):
            if data["weight"] <= threshold:
                out.append(v)
        return out

    def average_trust(self) -> float:
        weights = [d["weight"] for _, _, d in self.g.edges(data=True)]
        return sum(weights) / len(weights) if weights else 0.0

    def density(self) -> float:
        n = self.g.number_of_nodes()
        if n < 2:
            return 0.0
        possible = n * (n - 1)
        return self.g.number_of_edges() / possible

    def to_undirected_view(self) -> nx.Graph:
        ug = nx.Graph()
        for u, v, d in self.g.edges(data=True):
            w = d["weight"]
            if ug.has_edge(u, v):
                ug[u][v]["weight"] = (ug[u][v]["weight"] + w) / 2.0
            else:
                ug.add_edge(u, v, weight=w)
        return ug


def choose_action(
    agent: Agent,
    rng: random.Random,
    open_proposals: bool,
    nearby_agent: Optional[str],
    *,
    world=None,
    implemented_tools: Optional[Set[str]] = None,
) -> Tuple[str, dict]:
    """Personality-weighted tool selection."""
    p = agent.personality
    w = p.weights
    tool_scores: Dict[str, float] = {}

    def score(name: str, base: float) -> None:
        tool_scores[name] = tool_scores.get(name, 0.0) + base

    # Survival pressure
    if agent.energy < 35:
        score("rest", 2.5)
        score("gather_resources", 1.8)
    if agent.credits < 15:
        score("trade_offer", 1.2)
        score("gather_resources", 1.0)

    # Personality channels
    score("explore_cell", w[0] * 2.0)
    score("map_region", w[0] * 1.5)
    score("move_to_landmark", w[0] * 1.2)
    score("communicate", w[1] * 2.2)
    score("host_gathering", w[1] * 1.5)
    score("form_alliance", w[1] * 1.3)
    score("trade_offer", w[2] * 2.0)
    score("establish_market", w[2] * 1.2)
    score("audit_economy", w[2] * 1.0)
    score("vote_proposal", w[3] * (2.5 if open_proposals else 0.5))
    score("propose_constitution", w[3] * 0.8)
    score("amend_constitution", w[3] * 0.6)
    score("innovate_project", w[4] * 2.2)
    score("research_topic", w[4] * 1.5)
    score("build_structure", w[4] * 1.3)
    score("mediate_conflict", w[5] * 2.0)
    score("challenge_leader", w[5] * 1.2)

    # Preferred tools boost
    for t in p.preferred_tools:
        score(t, 0.9)

    if agent.energy < 22 and rng.random() < 0.06:
        score("commit_theft", 0.35)
        score("intimidate", 0.25)

    if nearby_agent:
        if nearby_agent in agent.alliances:
            score("trade_offer", 1.0)
            score("share_intel", 0.8)
        else:
            score("communicate", 0.7)

    if not tool_scores:
        return "rest", {}

    if world is not None and implemented_tools is not None:
        from tool_access import ToolAccessContext, list_available_tools, resolve_tool_name

        ctx = ToolAccessContext(
            open_proposals=open_proposals,
            pending_invitation=False,
            coop_partner_nearby=bool(nearby_agent and nearby_agent in agent.alliances),
        )
        allowed = set(
            list_available_tools(agent, world, ctx, implemented_tools)
        )
        # Map scores through resolve_tool_name
        filtered: Dict[str, float] = {}
        for t, sc in tool_scores.items():
            rt = resolve_tool_name(t)
            if t in allowed or rt in allowed:
                filtered[t] = sc
        if filtered:
            tool_scores = filtered

    tools = list(tool_scores.keys())
    weights = [max(0.05, tool_scores[t]) for t in tools]
    choice = rng.choices(tools, weights=weights, k=1)[0]
    params: dict = {}
    if choice in ("communicate", "trade_offer", "form_alliance", "share_intel", "mediate_conflict"):
        params["target"] = nearby_agent
    if choice == "move_to_landmark":
        params["landmark_id"] = None  # resolved in tools
    return choice, params


def clamp_energy(agent: Agent) -> None:
    agent.energy = max(0.0, min(MAX_ENERGY, agent.energy))
