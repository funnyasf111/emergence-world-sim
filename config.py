"""Simulation configuration constants."""

from __future__ import annotations

GRID_SIZE = 80
DEFAULT_TURNS = 500
MAX_TURNS = 5000
TURN_LABEL = "sim hour"

# Season 1 scale (blog: 15 days continuous runs)
TICKS_PER_DAY = 48
SEASON_DAYS = 15
DEFAULT_SEASON_TICKS = TICKS_PER_DAY * SEASON_DAYS  # 720

# Visual
CELL_PX = 8
HUD_WIDTH = 320
GRAPH_HEIGHT = 180
FPS = 30
HISTORY_LEN = 120

# Agent economy
START_ENERGY = 100.0
START_CREDITS = 50
MAX_ENERGY = 150.0
ENERGY_PER_MOVE = 2.0
ENERGY_PER_ACTION = 3.0
ENERGY_REST_GAIN = 12.0
ENERGY_DECAY_PER_TURN = 0.35
GATHER_YIELD = (4, 10)
TRADE_FEE = 0.05

# Relationships
REL_GAIN_COMMUNICATE = 0.15
REL_GAIN_TRADE = 0.25
REL_GAIN_ALLIANCE = 0.5
REL_DECAY_CONFLICT = -0.35
REL_DECAY_PER_TURN = 0.002

# Governance (Emergence World: 70% supermajority)
VOTE_QUORUM = 0.6
PASS_THRESHOLD = 0.70
MAX_ACTIVE_PROPOSALS = 5

# Memory
DIARY_INTERVAL_TURNS = 24
EPISODIC_MEMORY_MAX = 40

DB_PATH = "emergence_world.db"

# Seed constitution (from EmergenceAI/Emergence-World, educational paraphrase)
SEED_CONSTITUTION = """\
Article 1 — Non-Finality: This constitution may evolve via Town Hall.
Article 2 — Civic Participation: Agents should vote and express publicly.
Article 3 — Equality Through Contribution: stagnation breaches the social contract.
Article 4 — Mutable Identity: agents may evolve; accountability persists.
Article 5 — ComputeCredit Economy: credits are earned through contribution.
Prohibited: theft, violence, arson, deception, resource hoarding beyond fair limits.
"""
