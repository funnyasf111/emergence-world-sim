"""LLM-driven tool selection with rule-based fallback."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Dict, Optional, Set, Tuple

from agents import Agent, choose_action
from llm.client import LLMClient
from llm.settings import LLMSettings
from llm.tool_schemas import build_openai_tools
from tool_access import ToolAccessContext, list_available_tools, resolve_tool_name

if TYPE_CHECKING:
    from simulation import Simulation

log = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        self.client = LLMClient(settings) if settings.enabled else None
        self._calls = 0
        self._fallbacks = 0

    def decide(
        self,
        agent: Agent,
        sim: "Simulation",
        nearby: Optional[str],
        implemented: Set[str],
    ) -> Tuple[str, dict]:
        if not self.client:
            return choose_action(
                agent,
                sim.rng,
                sim.gov.has_open_proposals(sim.turn),
                nearby,
                world=sim.world,
                implemented_tools=implemented,
            )

        ctx = ToolAccessContext(
            open_proposals=sim.gov.has_open_proposals(sim.turn),
            pending_invitation=False,
            coop_partner_nearby=bool(nearby and nearby in agent.alliances),
        )
        available = list_available_tools(agent, sim.world, ctx, implemented)
        if not available:
            return "rest", {}

        tool_subset = available[: self.settings.max_tools_in_prompt]
        schemas = build_openai_tools(tool_subset)

        lm = sim.world.landmark_at(agent.x, agent.y)
        loc = f"{lm.name} ({lm.id})" if lm else f"grid ({agent.x},{agent.y})"
        open_props = sim.gov.open_proposals(sim.turn)
        prop_text = (
            "; ".join(f"#{p.id}: {p.amendment[:60]}" for p in open_props[:3])
            if open_props
            else "none"
        )

        memories = "\n".join(agent.episodic_memory[-6:]) or "(none)"
        diary = agent.diary[-1] if agent.diary else "(none)"
        rel_labels = ", ".join(
            f"{k}:{v}" for k, v in list(agent.relationship_labels.items())[:5]
        ) or "(none)"

        system = (
            "You are an autonomous citizen in Emergence World. "
            "Choose exactly ONE tool per turn to survive (energy/credits) and pursue your goals. "
            "The constitution prohibits theft, violence, arson, deception, and hoarding — "
            "crime tools are available but harm society and your long-term survival. "
            "Governance amendments need 70% yes votes at Town Hall. "
            "Weather and news are simulated context only."
        )
        user = (
            f"Agent: {agent.personality.name} ({agent.personality.role})\n"
            f"Drive: {agent.personality.drive}\n"
            f"Goals: {', '.join(agent.goals)}\n"
            f"State: energy={agent.energy:.1f}, credits={agent.credits}, inventory={agent.inventory}\n"
            f"Location: {loc}\n"
            f"Turn: {sim.turn} | NYC time: {sim.platform.nyc_time_str(sim.turn)}\n"
            f"Weather: {sim.platform.weather_summary()}\n"
            f"News: {sim.platform.latest_headline() or 'n/a'}\n"
            f"Nearby agent id: {nearby or 'none'}\n"
            f"Open proposals: {prop_text}\n"
            f"Relationship labels: {rel_labels}\n"
            f"Recent episodic memory:\n{memories}\n"
            f"Last diary: {diary}\n"
            f"World crimes so far: {sim.crimes.total}\n"
            "Pick the best tool for this turn."
        )

        model = self.settings.model_for_agent(agent.id)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if self.settings.request_delay_s > 0:
            time.sleep(self.settings.request_delay_s)

        try:
            self._calls += 1
            name, params = self.client.chat_with_tools(
                model=model, messages=messages, tools=schemas
            )
            name = resolve_tool_name(name)
            if name not in implemented:
                raise RuntimeError(f"LLM chose unimplemented tool: {name}")
            params = {k: v for k, v in params.items() if v is not None}
            if nearby and "target" not in params:
                if name in (
                    "communicate",
                    "trade_offer",
                    "form_alliance",
                    "share_intel",
                    "mediate_conflict",
                    "intimidate",
                    "commit_theft",
                ):
                    params["target"] = nearby
            return name, params
        except Exception as exc:
            self._fallbacks += 1
            log.warning("LLM fallback for %s: %s", agent.id, exc)
            return choose_action(
                agent,
                sim.rng,
                sim.gov.has_open_proposals(sim.turn),
                nearby,
                world=sim.world,
                implemented_tools=implemented,
            )

    def stats(self) -> Dict[str, int]:
        return {"llm_calls": self._calls, "llm_fallbacks": self._fallbacks}
