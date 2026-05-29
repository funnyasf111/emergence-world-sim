"""AWI-style aggregate wellbeing metrics (9 dimensions)."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from agents import Agent, RelationshipGraph
from governance import GovernanceState
from world import World


def compute_awi_metrics(
    agents: Dict[str, Agent],
    rel: RelationshipGraph,
    gov: GovernanceState,
    world: World,
    turn: int,
) -> Dict[str, float]:
    alive = [a for a in agents.values() if a.alive]
    n_alive = len(alive)
    n_total = len(agents)

    # 1. Population vitality
    vitality = (n_alive / max(1, n_total)) * (
        np.mean([a.energy for a in alive]) / 100.0 if alive else 0.0
    )

    # 2. Governance stability
    governance = gov.stability_score() * (0.5 + 0.5 * min(1.0, gov.version / 5.0))

    # 3. Economic equality (1 = equal)
    credits = [a.credits for a in alive] if alive else [0]
    if len(credits) > 1 and max(credits) > 0:
        gini = _gini(credits)
        economy = max(0.0, 1.0 - gini)
    else:
        economy = 0.5

    # 4. Social cohesion
    cohesion = (rel.average_trust() + 1.0) / 2.0

    # 5. Innovation index
    innov = sum(a.structures_built + a.trades_completed // 2 for a in alive)
    innovation = min(1.0, innov / (n_alive * 4.0 + 1))

    # 6. Conflict intensity (inverted for wellbeing)
    conflicts = sum(a.conflicts for a in agents.values())
    conflict_intensity = min(1.0, conflicts / (turn * 0.15 + 1))

    # 7. Resource sustainability
    mean_res = float(np.mean(world.resource_map))
    sustainability = min(1.0, mean_res * 1.2)

    # 8. Trust network density
    trust_density = (rel.density() + 1.0) / 2.0 * ((rel.average_trust() + 1) / 2)

    # 9. Cultural diversity (role spread + exploration)
    roles = len({a.personality.role for a in alive})
    diversity = (roles / max(1, n_total)) * (0.5 + 0.5 * world.exploration_ratio())

    return {
        "population_vitality": round(vitality, 4),
        "governance_stability": round(governance, 4),
        "economic_equality": round(economy, 4),
        "social_cohesion": round(cohesion, 4),
        "innovation_index": round(innovation, 4),
        "conflict_intensity": round(conflict_intensity, 4),
        "resource_sustainability": round(sustainability, 4),
        "trust_network_density": round(trust_density, 4),
        "cultural_diversity": round(diversity, 4),
        "composite_awi": round(
            (
                vitality
                + governance
                + economy
                + cohesion
                + innovation
                + (1.0 - conflict_intensity)
                + sustainability
                + trust_density
                + diversity
            )
            / 9.0,
            4,
        ),
    }


def _gini(values: List[float]) -> float:
    arr = np.array(sorted(values), dtype=float)
    if arr.sum() == 0:
        return 0.0
    n = len(arr)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr) + 1e-9))
