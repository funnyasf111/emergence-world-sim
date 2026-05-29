"""Turn-based simulation engine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from agents import Agent, RelationshipGraph, choose_action, clamp_energy
from config import (
    DEFAULT_TURNS,
    DIARY_INTERVAL_TURNS,
    ENERGY_DECAY_PER_TURN,
    GRID_SIZE,
    SEED_CONSTITUTION,
)
from crime_stats import CrimeStats
from governance import GovernanceState
from metrics import compute_awi_metrics
from persistence import Persistence
from personalities import AGENT_ROSTER
from platform_context import PlatformContext
from tool_access import catalog_count
from tools import TOOLS, ToolRuntime
from world import World

try:
    from llm.orchestrator import AgentOrchestrator
    from llm.settings import LLMSettings
except ImportError:
    AgentOrchestrator = None  # type: ignore
    LLMSettings = None  # type: ignore


@dataclass
class SimEvent:
    turn: int
    agent_id: str
    tool: str
    message: str
    success: bool


@dataclass
class Simulation:
    seed: int = 42
    max_turns: int = DEFAULT_TURNS
    world: World = field(default_factory=World)
    agents: Dict[str, Agent] = field(default_factory=dict)
    rel: RelationshipGraph = field(default_factory=RelationshipGraph)
    gov: GovernanceState = field(default_factory=lambda: GovernanceState(
        constitution_text="Initial constitution.", version=1
    ))
    db: Persistence = field(default_factory=Persistence)
    rng: random.Random = field(default_factory=random.Random)
    turn: int = 0
    running: bool = True
    paused: bool = False
    speed: float = 1.0
    recent_events: List[SimEvent] = field(default_factory=list)
    speech_log: List[str] = field(default_factory=list)
    metrics_history: List[Dict[str, float]] = field(default_factory=list)
    inspect_id: Optional[str] = None
    platform: PlatformContext = field(default_factory=PlatformContext)
    crimes: CrimeStats = field(default_factory=CrimeStats)
    use_llm: bool = False
    llm_settings: Optional["LLMSettings"] = None
    orchestrator: Optional["AgentOrchestrator"] = None
    database_url: Optional[str] = None

    def __post_init__(self) -> None:
        if self.database_url:
            from persistence_factory import create_persistence

            self.db = create_persistence(self.database_url)
        self.rng = random.Random(self.seed)
        self.world.seed(self.seed)
        self.platform.seed(self.seed)
        if self.use_llm and AgentOrchestrator is not None:
            settings = self.llm_settings or LLMSettings.from_env(enabled=True)
            settings.enabled = True
            try:
                self.orchestrator = AgentOrchestrator(settings)
            except ValueError:
                self.orchestrator = None
                self.use_llm = False
        if not self.agents:
            self.agents = Agent.create_all(self.rng, GRID_SIZE)
        self.rel.add_agents(list(self.agents.keys()))
        text, ver, _ = self.db.get_constitution()
        self.gov.constitution_text = text
        self.gov.version = ver
        self.turn = self.db.get_turn()

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)
        self.world.seed(self.seed)
        self.agents = Agent.create_all(self.rng, GRID_SIZE)
        self.rel = RelationshipGraph()
        self.rel.add_agents(list(self.agents.keys()))
        self.gov = GovernanceState(constitution_text=SEED_CONSTITUTION, version=1)
        self.crimes = CrimeStats()
        self.platform.seed(self.seed)
        self.turn = 0
        self.recent_events.clear()
        self.speech_log.clear()
        self.metrics_history.clear()
        if hasattr(self.db, "reset_all"):
            self.db.reset_all()
        elif getattr(self.db, "path", None) is not None:
            db_file = self.db.path
            if db_file.exists():
                db_file.unlink()
            self.db = Persistence()
        self._persist_constitution()
        if self.use_llm and LLMSettings and AgentOrchestrator:
            settings = self.llm_settings or LLMSettings.from_env(enabled=True)
            try:
                self.orchestrator = AgentOrchestrator(settings)
            except ValueError:
                self.orchestrator = None

    def _nearby(self, agent: Agent, radius: int = 3) -> Optional[str]:
        best, best_d = None, radius + 1
        for oid, other in self.agents.items():
            if oid == agent.id or not other.alive:
                continue
            d = abs(other.x - agent.x) + abs(other.y - agent.y)
            if d <= radius and d < best_d:
                best, best_d = oid, d
        return best

    def step_turn(self) -> List[SimEvent]:
        self.turn += 1
        self.platform.tick(self.turn)
        events: List[SimEvent] = []
        implemented = set(TOOLS._tools.keys())
        order = list(self.agents.values())
        self.rng.shuffle(order)

        for agent in order:
            if not agent.alive:
                continue
            if agent.energy <= 0:
                agent.alive = False
                msg = f"{agent.display_name()} collapsed from exhaustion"
                events.append(SimEvent(self.turn, agent.id, "death", msg, False))
                self.db.log_event(self.turn, "death", {"reason": "energy"}, agent.id)
                continue

            agent.energy -= ENERGY_DECAY_PER_TURN
            nearby = self._nearby(agent)
            if self.orchestrator:
                tool, params = self.orchestrator.decide(
                    agent, self, nearby, implemented
                )
            else:
                tool, params = choose_action(
                    agent,
                    self.rng,
                    self.gov.has_open_proposals(self.turn),
                    nearby,
                    world=self.world,
                    implemented_tools=implemented,
                )
            params["_runtime"] = ToolRuntime(platform=self.platform, crimes=self.crimes)
            if nearby:
                params["coop_partner_nearby"] = nearby in agent.alliances
            if tool == "move_to_landmark" and params.get("landmark_id") is None:
                lm = self.world.nearest_landmark(agent.x, agent.y)
                if lm:
                    params["landmark_id"] = lm.id
            if params.get("target") is None and nearby:
                params["target"] = nearby

            message, success = TOOLS.execute(
                tool,
                agent,
                self.world,
                self.agents,
                self.rel,
                self.gov,
                self.turn,
                self.rng,
                params,
            )
            clamp_energy(agent)
            if nearby:
                w = self.rel.get_weight(agent.id, nearby)
                if w >= 0.5:
                    agent.label_relationship(nearby, "ally")
                elif w <= -0.3:
                    agent.label_relationship(nearby, "rival")
                else:
                    agent.label_relationship(nearby, "acquaintance")
            ev = SimEvent(self.turn, agent.id, tool, message, success)
            events.append(ev)

            if agent.last_speech:
                line = f"T{self.turn} {agent.display_name()}: {agent.last_speech}"
                self.speech_log.append(line)
                self.speech_log = self.speech_log[-80:]

            self.db.add_memory(agent.id, self.turn, tool, message)
            self.db.save_agent(
                agent.id,
                agent.x,
                agent.y,
                agent.energy,
                agent.credits,
                agent.inventory,
                agent.goals,
                agent.alive,
                self.turn,
            )

        if self.turn % DIARY_INTERVAL_TURNS == 0:
            for ag in self.agents.values():
                if ag.alive:
                    ag.write_diary_entry(
                        self.turn,
                        f"{ag.personality.name}: {ag.personality.drive[:60]}",
                    )

        self.rel.decay_all(self.turn)
        for u, v, w in self._collect_rel_weights():
            self.db.save_relationship(u, v, w, self.turn)

        gov_msgs = self.gov.close_due_proposals(
            self.turn, sum(1 for a in self.agents.values() if a.alive)
        )
        for gm in gov_msgs:
            self.speech_log.append(f"T{self.turn} [Gov] {gm}")

        # Random constitution proposals
        if self.turn % 40 == 0:
            proposer = self.rng.choice([a for a in self.agents.values() if a.alive])
            self.gov.create_proposal(
                proposer.id,
                f"Public goods fund +{self.turn % 5} (sponsored by {proposer.personality.role})",
                self.turn,
            )

        metrics = compute_awi_metrics(
            self.agents, self.rel, self.gov, self.world, self.turn, self.crimes
        )
        self.metrics_history.append(metrics)
        self.metrics_history = self.metrics_history[-200:]
        self.db.save_metrics_snapshot(self.turn, metrics)
        self.db.set_turn(self.turn)
        self._persist_constitution()

        self.recent_events = events[-30:]
        return events

    def _collect_rel_weights(self) -> List[Tuple[str, str, float]]:
        out = []
        for u, v, d in self.rel.g.edges(data=True):
            out.append((u, v, float(d["weight"])))
        return out

    def _persist_constitution(self) -> None:
        self.db.save_constitution(
            self.gov.constitution_text, self.gov.version, self.turn
        )

    def run_batch(self, n: int = 1) -> None:
        for _ in range(n):
            if self.turn >= self.max_turns:
                self.running = False
                break
            self.step_turn()

    def final_metrics(self) -> Dict[str, float]:
        return compute_awi_metrics(
            self.agents, self.rel, self.gov, self.world, self.turn, self.crimes
        )

    def alive_count(self) -> int:
        return sum(1 for a in self.agents.values() if a.alive)
