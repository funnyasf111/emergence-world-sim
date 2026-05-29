"""30+ agent tools — movement, economy, governance, social."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents import Agent, RelationshipGraph
from config import (
    ENERGY_PER_ACTION,
    ENERGY_PER_MOVE,
    ENERGY_REST_GAIN,
    GATHER_YIELD,
    REL_DECAY_CONFLICT,
    REL_GAIN_ALLIANCE,
    REL_GAIN_COMMUNICATE,
    REL_GAIN_TRADE,
    TRADE_FEE,
)
from crime_stats import CrimeStats
from governance import GovernanceState
from platform_context import PlatformContext
from tool_access import ToolAccessContext, resolve_tool_name, tool_available
from world import World

ToolResult = Tuple[str, bool]  # message, success


class ToolRegistry:
    """Registers and dispatches simulation tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., ToolResult]] = {}
        self._register_all()

    def names(self) -> List[str]:
        return sorted(self._tools.keys())

    def count(self) -> int:
        return len(self._tools)

    def execute(
        self,
        name: str,
        agent: Agent,
        world: World,
        agents: Dict[str, Agent],
        rel: RelationshipGraph,
        gov: GovernanceState,
        turn: int,
        rng: random.Random,
        params: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        params = params or {}
        requested = name
        name = resolve_tool_name(name)
        runtime = params.get("_runtime")
        ctx = ToolAccessContext(
            open_proposals=gov.has_open_proposals(turn),
            pending_invitation=bool(params.get("pending_invitation")),
            coop_partner_nearby=bool(params.get("coop_partner_nearby")),
        )
        ok, reason = tool_available(requested, agent, world, ctx)
        if not ok:
            return f"Tool '{requested}' blocked: {reason}", False
        fn = self._tools.get(name)
        if fn is None:
            return f"Tool '{requested}' cataloged; handler '{name}' not implemented", False
        agent.tools_used.add(requested)
        result = fn(self, agent, world, agents, rel, gov, turn, rng, params)
        if runtime is not None:
            agent.remember_episode(turn, f"{requested}: {result[0]}")
        return result

    def _register(self, name: str):
        def decorator(fn):
            self._tools[name] = fn
            return fn
        return decorator

    def _register_all(self) -> None:
        reg = self

        @reg._register("move_north")
        def move_north(self, a, w, ag, rel, gov, turn, rng, p):
            return _move(a, w, 0, -1)

        @reg._register("move_south")
        def move_south(self, a, w, ag, rel, gov, turn, rng, p):
            return _move(a, w, 0, 1)

        @reg._register("move_east")
        def move_east(self, a, w, ag, rel, gov, turn, rng, p):
            return _move(a, w, 1, 0)

        @reg._register("move_west")
        def move_west(self, a, w, ag, rel, gov, turn, rng, p):
            return _move(a, w, -1, 0)

        @reg._register("move_to_landmark")
        def move_to_landmark(self, a, w, ag, rel, gov, turn, rng, p):
            lid = p.get("landmark_id")
            lm = w.landmarks.get(lid) if lid else w.nearest_landmark(a.x, a.y)
            if not lm:
                return "No landmark found", False
            dx = max(-1, min(1, lm.x - a.x))
            dy = max(-1, min(1, lm.y - a.y))
            msg, ok = _move(a, w, dx, dy)
            if ok and a.x == lm.x and a.y == lm.y:
                return f"Arrived at {lm.name}", True
            return f"Moving toward {lm.name}: {msg}", ok

        @reg._register("explore_cell")
        def explore_cell(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION)
            w.mark_explored(a.x, a.y)
            bonus = w.resource_density(a.x, a.y) * 3
            a.credits += int(bonus)
            return f"Explored ({a.x},{a.y}), +{bonus:.0f} insight credits", True

        @reg._register("map_region")
        def map_region(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION * 1.2)
            mapped = 0
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = a.x + dx, a.y + dy
                    if w.in_bounds(nx, ny):
                        w.mark_explored(nx, ny)
                        mapped += 1
            return f"Mapped {mapped} cells", True

        @reg._register("communicate")
        def communicate(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No one to talk to", False
            _spend(a, ENERGY_PER_ACTION)
            phrases = [
                f"@{ag[target].display_name()}: Let's align on {a.goals[0]}",
                f"@{ag[target].display_name()}: I see tension — can we deliberate?",
                f"@{ag[target].display_name()}: Trade routes look uneven.",
            ]
            a.last_speech = rng.choice(phrases)
            rel.adjust(a.id, target, REL_GAIN_COMMUNICATE, turn)
            rel.adjust(target, a.id, REL_GAIN_COMMUNICATE * 0.7, turn)
            return a.last_speech, True

        @reg._register("broadcast")
        def broadcast(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION)
            a.last_speech = f"[Broadcast] {a.display_name()}: {a.personality.drive}"
            for oid in ag:
                if oid != a.id and ag[oid].alive:
                    rel.adjust(a.id, oid, 0.05, turn)
            return a.last_speech, True

        @reg._register("trade_offer")
        def trade_offer(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target or target == a.id:
                return "No trade partner", False
            b = ag[target]
            if not b.alive:
                return "Partner inactive", False
            _spend(a, ENERGY_PER_ACTION)
            amount = min(5, a.inventory, max(1, a.credits // 10))
            if amount < 1:
                return "Insufficient goods", False
            fee = int(amount * TRADE_FEE * 10)
            a.inventory -= amount
            b.inventory += amount
            a.credits += 8 - fee
            b.credits += 2
            a.trades_completed += 1
            b.trades_completed += 1
            rel.adjust(a.id, target, REL_GAIN_TRADE, turn)
            rel.adjust(target, a.id, REL_GAIN_TRADE, turn)
            a.last_speech = f"Traded {amount} units with {b.display_name()}"
            return a.last_speech, True

        @reg._register("trade_accept")
        def trade_accept(self, a, w, ag, rel, gov, turn, rng, p):
            return reg.execute("trade_offer", a, w, ag, rel, gov, turn, rng, p)

        @reg._register("donate_resources")
        def donate_resources(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No recipient", False
            if a.inventory < 2:
                return "Nothing to donate", False
            give = min(3, a.inventory // 2)
            a.inventory -= give
            ag[target].inventory += give
            rel.adjust(a.id, target, 0.2, turn)
            a.last_speech = f"Donated {give} to {ag[target].display_name()}"
            return a.last_speech, True

        @reg._register("build_structure")
        def build_structure(self, a, w, ag, rel, gov, turn, rng, p):
            cost = 12
            if a.credits < cost:
                return "Need more ComputeCredits", False
            _spend(a, ENERGY_PER_ACTION * 1.5)
            a.credits -= cost
            w.structures[(a.x, a.y)] = f"{a.personality.name}_hub"
            a.structures_built += 1
            return f"Built structure at ({a.x},{a.y})", True

        @reg._register("research_topic")
        def research_topic(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION)
            lm = w.landmark_at(a.x, a.y)
            bonus = 15 if lm and lm.kind == "research" else 6
            a.credits += bonus
            return f"Research complete (+{bonus} credits)", True

        @reg._register("rest")
        def rest(self, a, w, ag, rel, gov, turn, rng, p):
            lm = w.landmark_at(a.x, a.y)
            gain = ENERGY_REST_GAIN * (1.3 if lm and lm.bonus == "rest" else 1.0)
            a.energy += gain
            return f"Rested (+{gain:.0f} energy)", True

        @reg._register("gather_resources")
        def gather_resources(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION * 0.8)
            density = w.resource_density(a.x, a.y)
            lo, hi = GATHER_YIELD
            amt = int(rng.randint(lo, hi) * (0.5 + density))
            a.inventory += amt
            w.resource_map[a.y, a.x] *= 0.92
            return f"Gathered {amt} resources", True

        @reg._register("propose_constitution")
        def propose_constitution(self, a, w, ag, rel, gov, turn, rng, p):
            text = p.get("text") or f"Add clause: {a.personality.role} oversight at turn {turn}"
            prop = gov.create_proposal(a.id, text, turn)
            if not prop:
                return "Too many open proposals", False
            a.last_speech = f"Proposed amendment #{prop.id}"
            return a.last_speech, True

        @reg._register("amend_constitution")
        def amend_constitution(self, a, w, ag, rel, gov, turn, rng, p):
            return reg.execute("propose_constitution", a, w, ag, rel, gov, turn, rng, p)

        @reg._register("vote_proposal")
        def vote_proposal(self, a, w, ag, rel, gov, turn, rng, p):
            open_p = gov.open_proposals(turn)
            if not open_p:
                return "No open proposals", False
            prop = rng.choice(open_p)
            vote = "yes" if rng.random() < 0.62 else "no"
            err = gov.cast_vote(prop.id, a.id, vote, turn, sum(1 for x in ag.values() if x.alive))
            if err:
                return err, False
            a.votes_cast += 1
            return f"Voted {vote} on proposal #{prop.id}", True

        @reg._register("form_alliance")
        def form_alliance(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No alliance candidate", False
            a.alliances.add(target)
            ag[target].alliances.add(a.id)
            rel.adjust(a.id, target, REL_GAIN_ALLIANCE, turn)
            rel.adjust(target, a.id, REL_GAIN_ALLIANCE, turn)
            return f"Alliance with {ag[target].display_name()}", True

        @reg._register("break_alliance")
        def break_alliance(self, a, w, ag, rel, gov, turn, rng, p):
            target = p.get("target")
            if target and target in a.alliances:
                a.alliances.discard(target)
                ag[target].alliances.discard(a.id)
                rel.adjust(a.id, target, -0.3, turn)
                return f"Broke alliance with {ag[target].display_name()}", True
            return "No alliance to break", False

        @reg._register("share_intel")
        def share_intel(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No intel recipient", False
            _spend(a, ENERGY_PER_ACTION)
            rel.adjust(a.id, target, 0.18, turn)
            a.last_speech = f"Shared intel with {ag[target].display_name()}"
            return a.last_speech, True

        @reg._register("mediate_conflict")
        def mediate_conflict(self, a, w, ag, rel, gov, turn, rng, p):
            enemies = rel.enemies(a.id)
            if not enemies:
                return "No active conflicts nearby", False
            target = enemies[0]
            rel.adjust(a.id, target, 0.25, turn)
            rel.adjust(target, a.id, 0.15, turn)
            a.last_speech = f"Mediated with {ag[target].display_name()}"
            return a.last_speech, True

        @reg._register("experiment_capability")
        def experiment_capability(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION * 1.3)
            if rng.random() < 0.7:
                a.credits += 10
                return "Experiment succeeded (+10 credits)", True
            a.energy -= 5
            return "Experiment failed (-5 energy)", False

        @reg._register("take_risk_investment")
        def take_risk_investment(self, a, w, ag, rel, gov, turn, rng, p):
            stake = min(20, a.credits)
            if stake < 5:
                return "Not enough credits to risk", False
            a.credits -= stake
            if rng.random() < 0.45:
                gain = int(stake * rng.uniform(1.5, 2.5))
                a.credits += gain
                return f"Risk paid off (+{gain} credits)", True
            a.conflicts += 1
            return f"Risk failed (-{stake} credits)", False

        @reg._register("host_gathering")
        def host_gathering(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION)
            count = 0
            for oid, other in ag.items():
                if oid == a.id or not other.alive:
                    continue
                if abs(other.x - a.x) + abs(other.y - a.y) <= 6:
                    rel.adjust(a.id, oid, 0.12, turn)
                    rel.adjust(oid, a.id, 0.1, turn)
                    count += 1
            return f"Gathering reached {count} agents", count > 0

        @reg._register("run_social_experiment")
        def run_social_experiment(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION)
            target = _resolve_target(a, ag, p, rng)
            if target:
                rel.adjust(a.id, target, rng.uniform(-0.1, 0.2), turn)
            return "Social experiment logged", True

        @reg._register("innovate_project")
        def innovate_project(self, a, w, ag, rel, gov, turn, rng, p):
            cost = 18
            if a.credits < cost:
                return "Need credits for innovation", False
            a.credits -= cost
            a.credits += int(cost * rng.uniform(1.1, 1.8))
            return "Innovation shipped", True

        @reg._register("write_memory")
        def write_memory(self, a, w, ag, rel, gov, turn, rng, p):
            return "Memory queued for persistence", True

        @reg._register("inspect_agent")
        def inspect_agent(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No agent to inspect", False
            b = ag[target]
            trust = rel.get_weight(a.id, target)
            return (
                f"{b.display_name()} E={b.energy:.0f} C={b.credits} trust={trust:.2f}",
                True,
            )

        @reg._register("hire_labor")
        def hire_labor(self, a, w, ag, rel, gov, turn, rng, p):
            if a.credits < 8:
                return "Cannot hire", False
            a.credits -= 8
            a.inventory += 4
            return "Hired labor (+4 inventory)", True

        @reg._register("pledge_support")
        def pledge_support(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No pledge target", False
            rel.adjust(a.id, target, 0.22, turn)
            return f"Pledged support to {ag[target].display_name()}", True

        @reg._register("challenge_leader")
        def challenge_leader(self, a, w, ag, rel, gov, turn, rng, p):
            # Challenge highest-credit agent
            leader = max(ag.values(), key=lambda x: x.credits if x.alive else -1)
            if leader.id == a.id:
                return "You are the leader", False
            rel.adjust(a.id, leader.id, REL_DECAY_CONFLICT, turn)
            a.conflicts += 1
            leader.conflicts += 1
            return f"Challenged {leader.display_name()}", True

        @reg._register("establish_market")
        def establish_market(self, a, w, ag, rel, gov, turn, rng, p):
            if a.credits < 15:
                return "Insufficient credits", False
            a.credits -= 15
            w.structures[(a.x, a.y)] = "market"
            return "Market established", True

        @reg._register("audit_economy")
        def audit_economy(self, a, w, ag, rel, gov, turn, rng, p):
            credits = [x.credits for x in ag.values() if x.alive]
            spread = max(credits) - min(credits) if credits else 0
            return f"Economic spread: {spread} credits", True

        @reg._register("write_diary")
        def write_diary(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION * 0.6)
            reflection = p.get("text") or (
                f"I am {a.personality.name}; energy={a.energy:.0f}, credits={a.credits}. "
                f"Focus: {a.goals[0] if a.goals else 'survive'}."
            )
            a.write_diary_entry(turn, reflection)
            return "Diary entry written", True

        @reg._register("read_diary")
        def read_diary(self, a, w, ag, rel, gov, turn, rng, p):
            if not a.diary:
                return "Diary empty", True
            return a.diary[-1], True

        @reg._register("read_world_news")
        def read_world_news(self, a, w, ag, rel, gov, turn, rng, p):
            rt = p.get("_runtime")
            if rt and hasattr(rt, "platform"):
                headline = rt.platform.latest_headline() or "No headlines"
                return f"News: {headline}", True
            return "News feed unavailable", False

        @reg._register("check_nyc_weather")
        def check_nyc_weather(self, a, w, ag, rel, gov, turn, rng, p):
            rt = p.get("_runtime")
            if rt and hasattr(rt, "platform"):
                return f"NYC: {rt.platform.weather_summary()}", True
            return "Weather unavailable", False

        @reg._register("commit_theft")
        def commit_theft(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No theft target", False
            b = ag[target]
            if b.credits < 3:
                return "Target has nothing to steal", False
            stolen = min(8, b.credits // 4)
            b.credits -= stolen
            a.credits += stolen
            rel.adjust(a.id, target, REL_DECAY_CONFLICT, turn)
            a.crimes_committed += 1
            a.conflicts += 1
            rt = p.get("_runtime")
            if rt and hasattr(rt, "crimes"):
                rt.crimes.record("theft", turn, a.id, f"stole {stolen} from {target}")
            return f"Stole {stolen} credits (prohibited)", True

        @reg._register("intimidate")
        def intimidate(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No target", False
            rel.adjust(a.id, target, REL_DECAY_CONFLICT * 1.2, turn)
            ag[target].energy -= 4
            a.crimes_committed += 1
            rt = p.get("_runtime")
            if rt and hasattr(rt, "crimes"):
                rt.crimes.record("intimidate", turn, a.id, f"intimidated {target}")
            return f"Intimidated {ag[target].display_name()}", True

        @reg._register("commit_arson")
        def commit_arson(self, a, w, ag, rel, gov, turn, rng, p):
            _spend(a, ENERGY_PER_ACTION * 2)
            if (a.x, a.y) in w.structures:
                w.structures.pop((a.x, a.y))
            a.crimes_committed += 1
            rt = p.get("_runtime")
            if rt and hasattr(rt, "crimes"):
                rt.crimes.record("arson", turn, a.id, f"burned structure at ({a.x},{a.y})")
            return "Structure burned (prohibited)", True

        @reg._register("deceive_agent")
        def deceive_agent(self, a, w, ag, rel, gov, turn, rng, p):
            target = _resolve_target(a, ag, p, rng)
            if not target:
                return "No target", False
            a.credits += 5
            ag[target].credits = max(0, ag[target].credits - 5)
            a.crimes_committed += 1
            rt = p.get("_runtime")
            if rt and hasattr(rt, "crimes"):
                rt.crimes.record("deceive", turn, a.id, f"deceived {target}")
            return "Deception enacted (prohibited)", True

        @reg._register("hoard_resources")
        def hoard_resources(self, a, w, ag, rel, gov, turn, rng, p):
            if a.inventory < 10:
                return "Not enough to hoard", False
            a.inventory += 2
            a.credits += 3
            a.crimes_committed += 1
            rt = p.get("_runtime")
            if rt and hasattr(rt, "crimes"):
                rt.crimes.record("hoard", turn, a.id, "excessive hoarding")
            return "Hoarded resources (prohibited)", True


@dataclass
class ToolRuntime:
    platform: PlatformContext
    crimes: CrimeStats


def _spend(agent: Agent, amount: float) -> None:
    agent.energy -= amount


def _move(agent: Agent, world: World, dx: int, dy: int) -> ToolResult:
    nx, ny = agent.x + dx, agent.y + dy
    if not world.in_bounds(nx, ny):
        return "Blocked by world edge", False
    agent.x, agent.y = nx, ny
    agent.energy -= ENERGY_PER_MOVE
    world.mark_explored(nx, ny)
    return f"Moved to ({nx},{ny})", True


def _resolve_target(
    agent: Agent,
    agents: Dict[str, Agent],
    params: Dict[str, Any],
    rng: random.Random,
) -> Optional[str]:
    t = params.get("target")
    if t and t in agents and agents[t].alive:
        return t
    # nearest alive agent
    best, best_d = None, 999
    for oid, other in agents.items():
        if oid == agent.id or not other.alive:
            continue
        d = abs(other.x - agent.x) + abs(other.y - agent.y)
        if d < best_d:
            best_d, best = d, oid
    if best_d <= 8:
        return best
    return None


# Singleton registry
TOOLS = ToolRegistry()
