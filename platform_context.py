"""Real-world context layer (NYC time, weather, news) — educational simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

NYC = ZoneInfo("America/New_York")

WEATHER_STATES = ("clear", "cloudy", "rain", "snow", "windy", "heat_advisory")
NEWS_TEMPLATES = (
    "NYC council debates transit funding package.",
    "Tech sector reports mixed earnings; markets watch Fed signals.",
    "Community organizers announce open forum on public safety.",
    "Weather service issues advisory for greater metro area.",
    "Researchers publish study on long-horizon AI agent coordination.",
    "Local arts collective opens exhibition on emergent social systems.",
)


@dataclass
class PlatformContext:
    """Synchronized external signals agents can react to (no live API keys required)."""

    rng: random.Random = field(default_factory=random.Random)
    sim_start: datetime = field(
        default_factory=lambda: datetime(2026, 5, 1, 8, 0, tzinfo=NYC)
    )
    weather: str = "clear"
    temperature_f: int = 62
    headlines: List[str] = field(default_factory=list)
    day_index: int = 1

    def seed(self, s: int) -> None:
        self.rng = random.Random(s)
        self.headlines = []
        self._refresh_news(3)

    def tick(self, turn: int) -> None:
        """Advance world clock and external conditions each sim hour."""
        if turn > 0 and turn % 48 == 0:
            self.day_index += 1
        if turn % 12 == 0:
            self.weather = self.rng.choice(WEATHER_STATES)
            self.temperature_f = int(self.rng.randint(28, 92))
        if turn % 8 == 0:
            self._refresh_news(1)

    def nyc_now(self, turn: int) -> datetime:
        return self.sim_start + timedelta(hours=turn)

    def nyc_time_str(self, turn: int) -> str:
        return self.nyc_now(turn).strftime("%Y-%m-%d %H:%M %Z")

    def weather_summary(self) -> str:
        return f"{self.weather}, {self.temperature_f}°F (NYC sync)"

    def latest_headline(self) -> Optional[str]:
        return self.headlines[-1] if self.headlines else None

    def _refresh_news(self, count: int) -> None:
        for _ in range(count):
            self.headlines.append(self.rng.choice(NEWS_TEMPLATES))
        self.headlines = self.headlines[-20:]
