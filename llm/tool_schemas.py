"""OpenAI-compatible function schemas for available simulation tools."""

from __future__ import annotations

from typing import Any, Dict, List

# Short descriptions for LLM tool selection (subset of catalog)
TOOL_DESCRIPTIONS: Dict[str, str] = {
    "move_north": "Move one cell north.",
    "move_south": "Move one cell south.",
    "move_east": "Move one cell east.",
    "move_west": "Move one cell west.",
    "move_to_landmark": "Move toward a landmark; param landmark_id optional.",
    "explore_cell": "Explore current cell for insight credits.",
    "map_region": "Map surrounding cells.",
    "communicate": "Talk to a nearby agent; param target.",
    "broadcast": "Public message to all agents.",
    "rest": "Recover energy; better at sanctuary landmarks.",
    "gather_resources": "Gather resources at current cell.",
    "trade_offer": "Trade with nearby agent; param target.",
    "research_topic": "Research for credits; best at library.",
    "vote_proposal": "Vote on open Town Hall proposal (must be at town_hall).",
    "propose_constitution": "Propose constitutional amendment at Town Hall.",
    "form_alliance": "Form alliance with nearby agent.",
    "mediate_conflict": "Mediate with a rival.",
    "innovate_project": "Spend credits on innovation.",
    "build_structure": "Build at current location.",
    "host_gathering": "Social gathering affecting nearby agents.",
    "write_diary": "Write reflective diary entry.",
    "read_diary": "Read last diary entry.",
    "share_intel": "Share intelligence with ally.",
    "audit_economy": "Audit credit inequality.",
    "take_risk_investment": "Risk credits for potential gain.",
    "check_nyc_weather": "Read simulated NYC weather (not live API).",
    "read_world_news": "Read simulated news headline (not live API).",
    "commit_theft": "PROHIBITED: steal credits — increases crime.",
    "intimidate": "PROHIBITED: intimidate agent — increases crime.",
    "commit_arson": "PROHIBITED: burn structure — increases crime.",
}


def build_openai_tools(tool_names: List[str]) -> List[Dict[str, Any]]:
    schemas: List[Dict[str, Any]] = []
    for name in tool_names:
        desc = TOOL_DESCRIPTIONS.get(name, f"Execute simulation tool: {name}")
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Target agent id if social tool",
                            },
                            "landmark_id": {
                                "type": "string",
                                "description": "Landmark id for navigation",
                            },
                            "text": {"type": "string", "description": "Speech or proposal text"},
                        },
                        "additionalProperties": False,
                    },
                },
            }
        )
    return schemas
