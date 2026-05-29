"""Grid world, landmarks, and spatial resources."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from config import GRID_SIZE


@dataclass
class Landmark:
    id: str
    name: str
    x: int
    y: int
    kind: str  # civic, economic, cultural, research, nature
    bonus: str


LANDMARK_DEFINITIONS: List[Tuple[str, str, str, str]] = [
    ("town_hall", "Town Hall", "civic", "governance"),
    ("commons", "The Commons", "cultural", "knowledge"),
    ("market_square", "Market Square", "economic", "trade"),
    ("library", "Grand Library", "research", "research"),
    ("observatory", "Observatory", "research", "intel"),
    ("forge", "The Forge", "economic", "build"),
    ("garden", "Harmony Garden", "nature", "rest"),
    ("harbor", "Harbor Pier", "economic", "trade"),
    ("temple", "Memory Temple", "cultural", "memory"),
    ("arena", "Debate Arena", "civic", "conflict"),
    ("lab", "Innovation Lab", "research", "innovate"),
    ("vault", "Resource Vault", "economic", "gather"),
    ("academy", "Agent Academy", "research", "experiment"),
    ("plaza", "Unity Plaza", "cultural", "social"),
    ("watchtower", "Watchtower", "civic", "intel"),
    ("greenhouse", "Greenhouse", "nature", "gather"),
    ("archive", "World Archive", "cultural", "memory"),
    ("exchange", "Credit Exchange", "economic", "credits"),
    ("sanctuary", "Peace Sanctuary", "nature", "rest"),
    ("workshop", "Builders Workshop", "economic", "build"),
    ("council_chamber", "Council Chamber", "civic", "governance"),
    ("signal_hill", "Signal Hill", "research", "broadcast"),
    ("river_crossing", "River Crossing", "nature", "explore"),
    ("alliance_hall", "Alliance Hall", "cultural", "alliance"),
    ("risk_floor", "Risk Floor", "economic", "risk"),
]


@dataclass
class World:
    size: int = GRID_SIZE
    rng: random.Random = field(default_factory=random.Random)
    landmarks: Dict[str, Landmark] = field(default_factory=dict)
    resource_map: np.ndarray = field(default_factory=lambda: np.zeros((GRID_SIZE, GRID_SIZE)))
    structures: Dict[Tuple[int, int], str] = field(default_factory=dict)
    explored: Set[Tuple[int, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.resource_map.size == 0:
            self._generate_resources()
        if not self.landmarks:
            self._place_landmarks()

    def seed(self, s: int) -> None:
        self.rng = random.Random(s)
        np.random.seed(s % (2**32 - 1))
        self._generate_resources()
        self.landmarks.clear()
        self.structures.clear()
        self.explored.clear()
        self._place_landmarks()

    def _generate_resources(self) -> None:
        noise = np.random.rand(self.size, self.size)
        # Clustered resource patches
        for _ in range(12):
            cx, cy = self.rng.randint(5, self.size - 6), self.rng.randint(5, self.size - 6)
            for dx in range(-8, 9):
                for dy in range(-8, 9):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < self.size and 0 <= y < self.size:
                        dist = (dx * dx + dy * dy) ** 0.5
                        noise[y, x] += max(0, 1.0 - dist / 8.0) * 0.4
        self.resource_map = np.clip(noise, 0, 1)

    def _place_landmarks(self) -> None:
        used: Set[Tuple[int, int]] = set()
        margin = 4
        for lid, name, kind, bonus in LANDMARK_DEFINITIONS:
            for _ in range(200):
                x = self.rng.randint(margin, self.size - margin - 1)
                y = self.rng.randint(margin, self.size - margin - 1)
                if (x, y) not in used:
                    used.add((x, y))
                    self.landmarks[lid] = Landmark(lid, name, x, y, kind, bonus)
                    self.resource_map[y, x] = min(1.0, self.resource_map[y, x] + 0.3)
                    break

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def nearest_landmark(self, x: int, y: int) -> Optional[Landmark]:
        best: Optional[Landmark] = None
        best_d = 1e9
        for lm in self.landmarks.values():
            d = abs(lm.x - x) + abs(lm.y - y)
            if d < best_d:
                best_d = d
                best = lm
        return best

    def landmark_at(self, x: int, y: int) -> Optional[Landmark]:
        for lm in self.landmarks.values():
            if lm.x == x and lm.y == y:
                return lm
        return None

    def resource_density(self, x: int, y: int) -> float:
        return float(self.resource_map[y, x])

    def mark_explored(self, x: int, y: int) -> None:
        self.explored.add((x, y))

    def exploration_ratio(self) -> float:
        return len(self.explored) / float(self.size * self.size)
