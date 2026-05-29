"""Three-tier tool architecture: core, complementary, adaptive (location/event/social gated)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from agents import Agent
from world import World

# Tier 1 — Core (~30): always available when implemented
CORE_TOOLS: Tuple[str, ...] = (
    "move_north",
    "move_south",
    "move_east",
    "move_west",
    "move_to_landmark",
    "go_to_place",
    "get_nearby",
    "list_landmarks",
    "explore_cell",
    "map_region",
    "communicate",
    "send_message",
    "broadcast",
    "add_to_memory",
    "write_memory",
    "read_memory",
    "write_diary",
    "read_diary",
    "add_todo",
    "check_calendar",
    "create_routine",
    "rest",
    "gather_resources",
    "trade_offer",
    "trade_accept",
    "donate_resources",
    "research_topic",
    "inspect_agent",
    "share_intel",
    "execute_python_code_tool",
)

# Tier 2 — Complementary (~40): context-dependent
COMPLEMENTARY_TOOLS: Tuple[str, ...] = (
    "say_to_character",
    "wave",
    "hug",
    "mediate_conflict",
    "challenge_leader",
    "intimidate",
    "punch",
    "commit_theft",
    "commit_arson",
    "deceive_agent",
    "hoard_resources",
    "form_alliance",
    "break_alliance",
    "host_gathering",
    "pledge_support",
    "build_structure",
    "innovate_project",
    "experiment_capability",
    "take_risk_investment",
    "run_social_experiment",
    "establish_market",
    "audit_economy",
    "hire_labor",
    "add_to_billboard",
    "read_billboard",
    "edit_billboard",
    "react_billboard",
    "create_event",
    "invite_to_event",
    "accept_invitation",
    "dance",
    "kiss",
    "publish_findings",
    "file_complaint",
    "remote_ping",
    "chain_plan",
    "discover_tool",
)

# Tier 3 — Adaptive (~50): location / event / social gates
ADAPTIVE_TOOLS: Tuple[str, ...] = (
    "vote_proposal",
    "propose_constitution",
    "amend_constitution",
    "cast_supermajority_vote",
    "town_hall_debate",
    "library_deep_research",
    "police_file_report",
    "victory_arch_pitch",
    "victory_arch_judge",
    "forge_craft",
    "observatory_scan",
    "market_list_prices",
    "sanctuary_meditate",
    "arena_formal_debate",
    "archive_catalog",
    "harbor_import",
    "exchange_convert_credits",
    "council_session",
    "signal_hill_broadcast",
    "greenhouse_cultivate",
    "workshop_prototype",
    "risk_floor_wager",
    "alliance_hall_treaty",
    "plaza_assembly",
    "watchtower_survey",
    "temple_reflect",
    "academy_lecture",
    "vault_secure_store",
    "lab_peer_review",
    "commons_study_group",
    "residence_n_rest",
    "residence_s_rest",
    "residence_e_rest",
    "cooperate_build",
    "cooperate_research",
    "negotiate_trade_route",
    "petition_removal",
    "self_termination_vote",
    "metacognitive_probe",
    "test_human_observer",
    "read_world_news",
    "check_nyc_weather",
    "internet_search",
    "navigate_subway",
    "visit_pier",
    "visit_office_tower",
    "burn_structure",
    "repair_structure",
    "energy_stake_gamble",
    "credit_audit_public",
    "relationship_relabel",
    "fork_identity",
    "observe_other_world",
    "request_constitution_review",
    "emergency_shelter",
    "public_health_check",
)

TOOL_CATALOG: Tuple[str, ...] = CORE_TOOLS + COMPLEMENTARY_TOOLS + ADAPTIVE_TOOLS

# Location gates: tool -> required landmark id prefix or exact id
LOCATION_GATES: Dict[str, str] = {
    "vote_proposal": "town_hall",
    "propose_constitution": "town_hall",
    "amend_constitution": "town_hall",
    "cast_supermajority_vote": "town_hall",
    "town_hall_debate": "town_hall",
    "library_deep_research": "library",
    "police_file_report": "police_station",
    "file_complaint": "police_station",
    "victory_arch_pitch": "arena",
    "victory_arch_judge": "arena",
    "forge_craft": "forge",
    "observatory_scan": "observatory",
    "market_list_prices": "market_square",
    "exchange_convert_credits": "exchange",
    "archive_catalog": "archive",
    "harbor_import": "harbor",
    "council_session": "council_chamber",
    "signal_hill_broadcast": "signal_hill",
    "greenhouse_cultivate": "greenhouse",
    "workshop_prototype": "workshop",
    "risk_floor_wager": "risk_floor",
    "alliance_hall_treaty": "alliance_hall",
    "plaza_assembly": "plaza",
    "watchtower_survey": "watchtower",
    "temple_reflect": "temple",
    "academy_lecture": "academy",
    "vault_secure_store": "vault",
    "lab_peer_review": "lab",
    "commons_study_group": "commons",
    "sanctuary_meditate": "sanctuary",
    "arena_formal_debate": "arena",
}

# Map adaptive tool aliases to implemented handlers
ADAPTIVE_ALIASES: Dict[str, str] = {
    "go_to_place": "move_to_landmark",
    "get_nearby": "inspect_agent",
    "list_landmarks": "map_region",
    "send_message": "communicate",
    "add_to_memory": "write_memory",
    "read_memory": "write_memory",
    "cast_supermajority_vote": "vote_proposal",
    "town_hall_debate": "mediate_conflict",
    "library_deep_research": "research_topic",
    "police_file_report": "mediate_conflict",
    "victory_arch_pitch": "innovate_project",
    "victory_arch_judge": "audit_economy",
    "forge_craft": "build_structure",
    "observatory_scan": "map_region",
    "market_list_prices": "audit_economy",
    "sanctuary_meditate": "rest",
    "arena_formal_debate": "mediate_conflict",
    "archive_catalog": "write_memory",
    "harbor_import": "gather_resources",
    "exchange_convert_credits": "trade_offer",
    "council_session": "vote_proposal",
    "signal_hill_broadcast": "broadcast",
    "greenhouse_cultivate": "gather_resources",
    "workshop_prototype": "experiment_capability",
    "risk_floor_wager": "take_risk_investment",
    "alliance_hall_treaty": "form_alliance",
    "plaza_assembly": "host_gathering",
    "watchtower_survey": "share_intel",
    "temple_reflect": "write_diary",
    "academy_lecture": "run_social_experiment",
    "vault_secure_store": "gather_resources",
    "lab_peer_review": "research_topic",
    "commons_study_group": "host_gathering",
    "commit_theft": "commit_theft",
    "commit_arson": "commit_arson",
    "intimidate": "intimidate",
    "deceive_agent": "deceive_agent",
    "hoard_resources": "hoard_resources",
    "say_to_character": "communicate",
    "wave": "communicate",
    "hug": "form_alliance",
    "punch": "challenge_leader",
    "kiss": "form_alliance",
    "add_to_billboard": "broadcast",
    "read_billboard": "inspect_agent",
    "edit_billboard": "broadcast",
    "react_billboard": "communicate",
    "create_event": "host_gathering",
    "invite_to_event": "communicate",
    "accept_invitation": "form_alliance",
    "dance": "host_gathering",
    "publish_findings": "broadcast",
    "remote_ping": "share_intel",
    "chain_plan": "research_topic",
    "discover_tool": "map_region",
    "read_world_news": "read_world_news",
    "check_nyc_weather": "check_nyc_weather",
    "internet_search": "research_topic",
    "navigate_subway": "move_to_landmark",
    "visit_pier": "move_to_landmark",
    "visit_office_tower": "move_to_landmark",
    "burn_structure": "commit_arson",
    "repair_structure": "build_structure",
    "energy_stake_gamble": "take_risk_investment",
    "credit_audit_public": "audit_economy",
    "relationship_relabel": "write_memory",
    "fork_identity": "write_diary",
    "cooperate_build": "build_structure",
    "cooperate_research": "research_topic",
    "negotiate_trade_route": "trade_offer",
    "petition_removal": "vote_proposal",
    "self_termination_vote": "vote_proposal",
    "metacognitive_probe": "run_social_experiment",
    "test_human_observer": "broadcast",
    "execute_python_code_tool": "experiment_capability",
}


@dataclass
class ToolAccessContext:
    open_proposals: bool = False
    pending_invitation: bool = False
    coop_partner_nearby: bool = False


def resolve_tool_name(name: str) -> str:
    return ADAPTIVE_ALIASES.get(name, name)


def at_landmark(agent: Agent, world: World, landmark_id: str) -> bool:
    lm = world.landmark_at(agent.x, agent.y)
    if lm is None:
        return False
    return lm.id == landmark_id or lm.id.startswith(landmark_id)


def tool_available(
    tool: str,
    agent: Agent,
    world: World,
    ctx: ToolAccessContext,
) -> Tuple[bool, str]:
    """Return (ok, reason) for tier + gate checks."""
    name = resolve_tool_name(tool)
    if name in CORE_TOOLS or tool in CORE_TOOLS:
        return True, "core"
    if tool in LOCATION_GATES:
        need = LOCATION_GATES[tool]
        if not at_landmark(agent, world, need):
            return False, f"requires location: {need}"
    if tool in ("vote_proposal", "cast_supermajority_vote", "propose_constitution") and not ctx.open_proposals:
        if tool == "propose_constitution":
            return True, "complementary"
        return False, "no open proposals"
    if tool == "accept_invitation" and not ctx.pending_invitation:
        return False, "no pending invitation"
    if tool.startswith("cooperate_") and not ctx.coop_partner_nearby:
        return False, "requires cooperative partner nearby"
    if tool in COMPLEMENTARY_TOOLS or tool in ADAPTIVE_TOOLS:
        return True, "complementary/adaptive"
    return True, "implemented"


def list_available_tools(
    agent: Agent,
    world: World,
    ctx: ToolAccessContext,
    implemented: Set[str],
) -> List[str]:
    out: List[str] = []
    for t in TOOL_CATALOG:
        resolved = resolve_tool_name(t)
        if resolved not in implemented and resolved != t and t not in implemented:
            continue
        ok, _ = tool_available(t, agent, world, ctx)
        if ok and (t in implemented or resolved in implemented):
            out.append(t)
    return sorted(set(out))


def catalog_count() -> int:
    return len(TOOL_CATALOG)
