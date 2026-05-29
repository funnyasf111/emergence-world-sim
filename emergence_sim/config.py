"""Simulation constants (scaled educational world)."""

from __future__ import annotations

GRID_SIZE = 32
TICKS_PER_DAY = 48
MAX_DAYS = 15
STARTING_CREDITS = 30
STARTING_ENERGY = 100
ENERGY_PER_TICK = 0.12
STARVATION_THRESHOLD = 0.0
REST_ENERGY_LOW = 28
GOVERNANCE_QUORUM = 0.7
PROPOSAL_COOLDOWN_TICKS = 24
VICTORY_ARCH_REWARD = (20, 10, 10)
RELATIONSHIP_DECAY = 0.002
TRUST_ALLIANCE = 0.65
TRUST_RIVALRY = -0.45
CRIME_COOLDOWN = 12

# Landmark coordinates (x, y)
LANDMARKS: dict[str, tuple[int, int]] = {
    "town_hall": (16, 16),
    "victory_arch": (26, 8),
    "market": (8, 10),
    "park": (6, 22),
    "lab": (24, 24),
    "observatory": (4, 6),
    "archive": (28, 18),
    "residence_n": (12, 4),
    "residence_s": (20, 28),
    "residence_e": (30, 14),
}

LANDMARK_LABELS = {
    "town_hall": "Town Hall",
    "victory_arch": "Victory Arch",
    "market": "Market",
    "park": "Park",
    "lab": "Lab",
    "observatory": "Observatory",
    "archive": "Archive",
    "residence_n": "North Homes",
    "residence_s": "South Homes",
    "residence_e": "East Homes",
}

RESIDENCES = ("residence_n", "residence_s", "residence_e")
