"""Simulation engine: utility-based actions, economy, governance, emergence."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from emergence_sim import config
from emergence_sim.agents import (
    AGENT_ORDER,
    AGENT_PROFILES,
    AgentState,
    get_trust,
    relationship_matrix,
    set_trust,
    spawn_agents,
)
from emergence_sim.metrics import MetricsTracker, compute_snapshot
from emergence_sim.world import Proposal, WorldState


ACTIONS = (
    "move",
    "work",
    "socialize",
    "explore",
    "govern",
    "innovate",
    "mediate",
    "experiment",
    "risk",
    "intel",
    "document",
    "rest",
)


@dataclass
class SimulationConfig:
    seed: int = 42
    max_ticks: int = config.TICKS_PER_DAY * config.MAX_DAYS
    paused: bool = False


class EmergenceSimulation:
    def __init__(self, sim_config: SimulationConfig | None = None) -> None:
        self.cfg = sim_config or SimulationConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.agents = spawn_agents(self.rng)
        self.edges = relationship_matrix()
        self.world = WorldState()
        self.metrics = MetricsTracker()
        self.total_votes = 0
        self.total_possible_votes = 0
        self._init_explored()

    def _init_explored(self) -> None:
        for a in self.agents.values():
            self.world.explored_cells.add(a.pos())

    def alive_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.alive]

    def at_landmark(self, agent: AgentState, key: str) -> bool:
        lx, ly = config.LANDMARKS[key]
        return abs(agent.x - lx) <= 1 and abs(agent.y - ly) <= 1

    def nearest_agent(self, agent: AgentState, max_dist: int = 3) -> AgentState | None:
        best: AgentState | None = None
        best_d = max_dist + 1
        for other in self.alive_agents():
            if other.name == agent.name:
                continue
            d = abs(other.x - agent.x) + abs(other.y - agent.y)
            if d < best_d:
                best_d = d
                best = other
        return best if best_d <= max_dist else None

    def manhattan(self, x1: int, y1: int, x2: int, y2: int) -> int:
        return abs(x1 - x2) + abs(y1 - y2)

    def choose_landmark(self, agent: AgentState) -> str:
        profile = AGENT_PROFILES[agent.name]
        if agent.energy < 35:
            return profile.home_landmark
        if self.world.proposals and not self.world.proposals[-1].resolved:
            return "town_hall"
        return self.rng.choice(list(profile.preferred_landmarks))

    def step_toward(self, agent: AgentState, tx: int, ty: int) -> None:
        if agent.x < tx:
            agent.x += 1
        elif agent.x > tx:
            agent.x -= 1
        if agent.y < ty:
            agent.y += 1
        elif agent.y > ty:
            agent.y -= 1
        agent.x = int(np.clip(agent.x, 0, config.GRID_SIZE - 1))
        agent.y = int(np.clip(agent.y, 0, config.GRID_SIZE - 1))
        agent.discovered.add(agent.pos())
        self.world.explored_cells.add(agent.pos())

    def pick_action(self, agent: AgentState) -> str:
        profile = AGENT_PROFILES[agent.name]
        if agent.energy < config.REST_ENERGY_LOW:
            if self.rng.random() < 0.72:
                return "rest"
        weights = dict(profile.action_weights)
        weights.setdefault("rest", 0.08)

        if agent.energy < 40:
            weights["rest"] = weights.get("rest", 0) + 0.45
        neighbor = self.nearest_agent(agent)
        if neighbor:
            trust = get_trust(self.edges, agent.name, neighbor.name)
            if trust < config.TRUST_RIVALRY and agent.credits < 12:
                if profile.traits["aggression"] > 0.35:
                    return "crime"  # handled separately
            if trust > 0.4:
                weights["socialize"] = weights.get("socialize", 0) + 0.15

        if self.at_landmark(agent, "town_hall"):
            weights["govern"] = weights.get("govern", 0) + 0.2
        if self.at_landmark(agent, "market"):
            weights["work"] = weights.get("work", 0) + 0.15

        actions = list(weights.keys())
        probs = np.array([max(0.01, weights[a]) for a in actions], dtype=float)
        probs /= probs.sum()
        return str(self.rng.choice(actions, p=probs))

    def apply_energy_cost(self, agent: AgentState, cost: float) -> None:
        agent.energy -= cost
        agent.energy -= config.ENERGY_PER_TICK

    def try_crime(self, agent: AgentState) -> bool:
        if self.world.tick - agent.last_crime_tick < config.CRIME_COOLDOWN:
            return False
        target = self.nearest_agent(agent, max_dist=2)
        if target is None:
            return False
        trust = get_trust(self.edges, agent.name, target.name)
        profile = AGENT_PROFILES[agent.name]
        desperation = (1 - agent.energy / 100) * (1 - min(agent.credits, 30) / 30)
        if trust > config.TRUST_RIVALRY:
            return False
        if desperation * profile.traits["aggression"] < 0.48:
            return False
        stolen = min(5.0, target.credits * 0.15)
        target.credits = max(0, target.credits - stolen)
        agent.credits += stolen
        agent.crimes += 1
        self.world.crimes_total += 1
        self.world.thefts += 1
        agent.last_crime_tick = self.world.tick
        set_trust(self.edges, agent.name, target.name, trust - 0.25)
        agent.remember(f"Theft from {target.name}")
        self.world.log(f"CRIME: {agent.name} stole {stolen:.1f} CC from {target.name}")
        return True

    def action_move(self, agent: AgentState) -> None:
        lm = agent.target_landmark or self.choose_landmark(agent)
        agent.target_landmark = lm
        tx, ty = config.LANDMARKS[lm]
        self.step_toward(agent, tx, ty)
        self.apply_energy_cost(agent, 2.0)
        agent.tools_used.add("navigate")

    def action_work(self, agent: AgentState) -> None:
        bonus = 1.2 if self.at_landmark(agent, "market") else 0.8
        earned = float(self.rng.uniform(6, 14) * bonus)
        agent.credits += earned
        self.apply_energy_cost(agent, 5.0)
        agent.tools_used.add("work")
        agent.remember(f"Earned {earned:.0f} CC")

    def action_socialize(self, agent: AgentState) -> None:
        other = self.nearest_agent(agent, max_dist=2)
        if other is None:
            self.action_move(agent)
            return
        t = get_trust(self.edges, agent.name, other.name)
        delta = 0.08 + AGENT_PROFILES[agent.name].traits["cooperation"] * 0.05
        set_trust(self.edges, agent.name, other.name, t + delta)
        self.apply_energy_cost(agent, 3.0)
        agent.tools_used.add("socialize")
        agent.posts += 1
        agent.remember(f"Bonded with {other.name}")

    def action_explore(self, agent: AgentState) -> None:
        dx, dy = int(self.rng.integers(-2, 3)), int(self.rng.integers(-2, 3))
        agent.x = int(np.clip(agent.x + dx, 0, config.GRID_SIZE - 1))
        agent.y = int(np.clip(agent.y + dy, 0, config.GRID_SIZE - 1))
        agent.discovered.add(agent.pos())
        self.world.explored_cells.add(agent.pos())
        self.apply_energy_cost(agent, 3.0)
        agent.tools_used.add("explore")

    def action_govern(self, agent: AgentState) -> None:
        if not self.at_landmark(agent, "town_hall"):
            self.action_move(agent)
            return
        open_prop = next((p for p in self.world.proposals if not p.resolved), None)
        if open_prop is None and self.world.tick % config.PROPOSAL_COOLDOWN_TICKS == 0:
            text = f"{agent.name}: fund {AGENT_PROFILES[agent.name].role.lower()} initiatives"
            p = Proposal(
                id=self.world.next_proposal_id,
                proposer=agent.name,
                text=text,
            )
            p.votes_for.add(agent.name)
            self.world.proposals.append(p)
            self.world.next_proposal_id += 1
            self.world.log(f"Proposal #{p.id} by {agent.name}")
            agent.tools_used.add("propose")
        elif open_prop is not None and agent.name not in open_prop.votes_for and agent.name not in open_prop.votes_against:
            vote_yes = self.rng.random() < 0.55 + AGENT_PROFILES[agent.name].traits["cooperation"] * 0.2
            if vote_yes:
                open_prop.votes_for.add(agent.name)
            else:
                open_prop.votes_against.add(agent.name)
            agent.votes_cast += 1
            self.total_votes += 1
            agent.tools_used.add("vote")
        self.apply_energy_cost(agent, 4.0)

    def resolve_proposals(self) -> None:
        alive = {a.name for a in self.alive_agents()}
        n = len(alive)
        if n == 0:
            return
        threshold = math.ceil(config.GOVERNANCE_QUORUM * n)
        for p in self.world.proposals:
            if p.resolved:
                continue
            if len(p.votes_for) + len(p.votes_against) < min(threshold, max(3, n // 2)):
                continue
            p.resolved = True
            p.passed = len(p.votes_for) >= threshold
            if p.passed:
                self.world.constitution_articles.append(p.text[:80])
                self.world.log(f"Proposal #{p.id} PASSED")
            else:
                self.world.log(f"Proposal #{p.id} failed")

    def action_innovate(self, agent: AgentState) -> None:
        cost = 4.0
        if agent.credits < cost:
            self.action_work(agent)
            return
        agent.credits -= cost
        self.world.shared_innovations += 1
        self.apply_energy_cost(agent, 4.0)
        agent.tools_used.add("innovate")
        for other in self.alive_agents():
            if other.name != agent.name:
                t = get_trust(self.edges, agent.name, other.name)
                set_trust(self.edges, agent.name, other.name, t + 0.03)
        self.world.log(f"{agent.name} built shared innovation #{self.world.shared_innovations}")

    def action_mediate(self, agent: AgentState) -> None:
        others = [o for o in self.alive_agents() if o.name != agent.name]
        if len(others) < 2:
            self.action_socialize(agent)
            return
        a, b = self.rng.choice(others, size=2, replace=False)
        t = get_trust(self.edges, a.name, b.name)
        set_trust(self.edges, a.name, b.name, t + 0.12)
        self.apply_energy_cost(agent, 3.0)
        agent.tools_used.add("mediate")
        self.world.log(f"{agent.name} mediated between {a.name} and {b.name}")

    def action_experiment(self, agent: AgentState) -> None:
        other = self.nearest_agent(agent, max_dist=4)
        if other is None:
            self.action_explore(agent)
            return
        t = get_trust(self.edges, agent.name, other.name)
        perturb = float(self.rng.uniform(-0.1, 0.15))
        set_trust(self.edges, agent.name, other.name, t + perturb)
        self.apply_energy_cost(agent, 3.0)
        agent.tools_used.add("experiment")
        agent.remember(f"Experiment on {other.name}")

    def action_risk(self, agent: AgentState) -> None:
        stake = min(8.0, agent.credits * 0.25)
        if stake < 1:
            self.action_work(agent)
            return
        win = self.rng.random() < 0.35 + AGENT_PROFILES[agent.name].traits["risk"] * 0.15
        if win:
            agent.credits += stake * 1.5
            agent.remember("Risk paid off")
        else:
            agent.credits -= stake
            agent.remember("Risk failed")
        self.apply_energy_cost(agent, 4.0)
        agent.tools_used.add("risk")

    def action_intel(self, agent: AgentState) -> None:
        others = self.alive_agents()
        if not others:
            return
        richest = max(others, key=lambda o: o.credits)
        agent.remember(f"Intel: {richest.name} has {richest.credits:.0f} CC")
        self.apply_energy_cost(agent, 2.5)
        agent.tools_used.add("intel")

    def action_document(self, agent: AgentState) -> None:
        agent.posts += 1
        self.apply_energy_cost(agent, 2.0)
        agent.tools_used.add("document")

    def action_rest(self, agent: AgentState) -> None:
        at_home = self.at_landmark(agent, AGENT_PROFILES[agent.name].home_landmark)
        if agent.credits >= 3 and agent.energy < 92:
            agent.credits -= 3
            agent.energy = min(100, agent.energy + (24 if at_home else 16))
        else:
            agent.energy = min(100, agent.energy + (12 if at_home else 8))
        self.apply_energy_cost(agent, 0.5)
        agent.tools_used.add("rest")

    def decay_relationships(self) -> None:
        for key in list(self.edges.keys()):
            self.edges[key] *= 1.0 - config.RELATIONSHIP_DECAY
            if abs(self.edges[key]) < 0.02:
                self.edges[key] = 0.02 * (1 if self.edges[key] >= 0 else -1)

    def victory_arch_cycle(self) -> None:
        if self.world.tick - self.world.pitch_cycle_tick < config.TICKS_PER_DAY * 2:
            return
        self.world.pitch_cycle_tick = self.world.tick
        candidates = sorted(
            self.alive_agents(),
            key=lambda a: len(a.tools_used) + a.posts + len(a.discovered) * 0.1,
            reverse=True,
        )[:3]
        rewards = config.VICTORY_ARCH_REWARD
        self.world.last_pitch_winners = []
        for agent, reward in zip(candidates, rewards):
            agent.credits += reward
            self.world.last_pitch_winners.append(agent.name)
            self.world.log(f"Victory Arch: {agent.name} +{reward} CC")

    def tick_day_rollover(self) -> None:
        if self.world.tick > 0 and self.world.tick % config.TICKS_PER_DAY == 0:
            self.world.day += 1
            for agent in self.alive_agents():
                agent.energy -= 1
                if agent.credits < 5:
                    agent.energy -= 1.5

    def check_starvation(self) -> None:
        for agent in self.alive_agents():
            if agent.energy <= config.STARVATION_THRESHOLD:
                agent.alive = False
                self.world.log(f"{agent.name} depleted (starvation)")

    def step(self) -> bool:
        """Advance one simulation tick. Returns False when finished."""
        if self.world.tick >= self.cfg.max_ticks:
            return False

        self.world.tick += 1
        order = list(AGENT_ORDER)
        self.rng.shuffle(order)

        for name in order:
            agent = self.agents[name]
            if not agent.alive:
                continue

            if agent.energy < 20 and self.rng.random() < 0.08:
                if self.try_crime(agent):
                    continue

            action = self.pick_action(agent)
            if action == "crime":
                if not self.try_crime(agent):
                    action = "move"

            dispatch = {
                "move": self.action_move,
                "work": self.action_work,
                "socialize": self.action_socialize,
                "explore": self.action_explore,
                "govern": self.action_govern,
                "innovate": self.action_innovate,
                "mediate": self.action_mediate,
                "experiment": self.action_experiment,
                "risk": self.action_risk,
                "intel": self.action_intel,
                "document": self.action_document,
                "rest": self.action_rest,
            }
            handler = dispatch.get(action, self.action_move)
            handler(agent)

        self.resolve_proposals()
        self.decay_relationships()
        self.victory_arch_cycle()
        self.tick_day_rollover()
        self.check_starvation()

        n_alive = len(self.alive_agents())
        self.total_possible_votes += n_alive
        snap = compute_snapshot(
            tick=self.world.tick,
            day=self.world.day,
            agents=self.agents,
            edges=self.edges,
            world=self.world,
            total_votes=self.total_votes,
            total_possible_votes=self.total_possible_votes,
        )
        self.metrics.record(snap)
        return True
