"""Emergence World Gazette — major incidents only (death, violence, crime, big governance)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from config import TICKS_PER_DAY

if TYPE_CHECKING:
    from simulation import SimEvent, Simulation

PAPER_NAME = "The Emergence Gazette"
TAGLINE_MAJOR = "Major incidents only — death, violence, crime, constitutional upheaval"
TAGLINE_FULL = "Full chronicle of Emergence World"

# Tools that always make the paper in major-only mode
MAJOR_TOOLS: Set[str] = {
    "death",
    "commit_theft",
    "commit_arson",
    "intimidate",
    "deceive_agent",
    "hoard_resources",
    "punch",
    "challenge_leader",
    "break_alliance",
    "governance",
    "crime",
    "daily_roundup",
}

SECTION_ORDER = (
    "front_page",
    "obituaries",
    "crime",
    "civic",
    "society",
)

SECTION_TITLES = {
    "front_page": "Front Page",
    "obituaries": "Obituaries",
    "crime": "Crime & Public Order",
    "civic": "Constitutional Crisis",
    "society": "Conflict & Rupture",
}


@dataclass
class Story:
    turn: int
    day: int
    section: str
    headline: str
    body: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    importance: int = 1
    tool: Optional[str] = None

    @property
    def dateline(self) -> str:
        return f"Day {self.day}, Hour {self.turn % TICKS_PER_DAY or TICKS_PER_DAY}"


@dataclass
class NewspaperFeed:
    major_only: bool = True
    stories: List[Story] = field(default_factory=list)
    _seen_crimes: Set[str] = field(default_factory=set)
    _major_count_by_day: Dict[int, int] = field(default_factory=dict)
    _population_start: int = 10

    def clear(self) -> None:
        self.stories.clear()
        self._seen_crimes.clear()
        self._major_count_by_day.clear()
        self._population_start = 10

    def _add(self, story: Story) -> None:
        if self.major_only and not _is_major_story(story):
            return
        self.stories.append(story)
        self._major_count_by_day[story.day] = self._major_count_by_day.get(story.day, 0) + 1

    def ingest_turn(
        self,
        sim: "Simulation",
        events: List["SimEvent"],
        gov_messages: List[str],
        proposal_created: bool = False,
    ) -> None:
        turn = sim.turn
        day = max(1, (turn - 1) // TICKS_PER_DAY + 1)
        alive_before = sim.alive_count()

        for ev in events:
            agent = sim.agents.get(ev.agent_id)
            name = agent.display_name() if agent else ev.agent_id
            section, headline, importance = _classify(ev.tool, ev.message, ev.success)

            if section == "skip":
                continue
            if self.major_only and ev.tool not in MAJOR_TOOLS:
                continue

            body = _format_body(ev, name, sim)
            self._add(
                Story(
                    turn=turn,
                    day=day,
                    section=section,
                    headline=headline,
                    body=body,
                    agent_id=ev.agent_id,
                    agent_name=name,
                    importance=importance,
                    tool=ev.tool,
                )
            )

            if ev.tool == "death":
                self._add(
                    Story(
                        turn=turn,
                        day=day,
                        section="obituaries",
                        headline=f"DEATH: {name} has fallen",
                        body=(
                            f"{name} ({agent.personality.role if agent else 'Citizen'}) "
                            f"is gone — energy depleted at turn {turn}. "
                            f"{sim.alive_count()} citizens remain."
                        ),
                        agent_id=ev.agent_id,
                        agent_name=name,
                        importance=5,
                        tool="death",
                    )
                )

        for gm in gov_messages:
            if self.major_only and "PASSED" not in gm.upper():
                continue
            self._add(
                Story(
                    turn=turn,
                    day=day,
                    section="front_page",
                    headline=_gov_headline(gm),
                    body=gm,
                    importance=5,
                    tool="governance",
                )
            )

        if not self.major_only and proposal_created:
            open_p = sim.gov.open_proposals(turn)
            if open_p:
                p = open_p[-1]
                proposer = sim.agents.get(p.proposer)
                pname = proposer.display_name() if proposer else p.proposer
                self._add(
                    Story(
                        turn=turn,
                        day=day,
                        section="civic",
                        headline=f"New proposal #{p.id} enters Town Hall docket",
                        body=(
                            f"{pname} submitted: \"{p.amendment}\". "
                            f"Voting closes turn {p.closes_turn}."
                        ),
                        agent_id=p.proposer,
                        agent_name=pname,
                        importance=3,
                        tool="propose_constitution",
                    )
                )

        for line in sim.crimes.log:
            if line not in self._seen_crimes:
                self._seen_crimes.add(line)
                self._add(
                    Story(
                        turn=turn,
                        day=day,
                        section="crime",
                        headline=_crime_headline(line),
                        body=line,
                        importance=5,
                        tool="crime",
                    )
                )

        if turn % TICKS_PER_DAY == 0:
            self._maybe_daily_roundup(sim, day, alive_before)

    def _maybe_daily_roundup(self, sim: "Simulation", day: int, alive_before: int) -> None:
        had_major = self._major_count_by_day.get(day, 0) > 0
        population_drop = sim.alive_count() < alive_before
        if self.major_only and not had_major and not population_drop:
            return
        if not self.major_only:
            return  # full mode handled elsewhere if re-enabled later

        self._add(
            Story(
                turn=sim.turn,
                day=day,
                section="front_page",
                headline=f"Day {day} roundup: {sim.crimes.total} crimes, {sim.alive_count()}/10 alive",
                body=(
                    f"Population change: {alive_before} → {sim.alive_count()}. "
                    f"Total crimes: {sim.crimes.total}. "
                    f"AWI: {sim.final_metrics().get('composite_awi', 0):.3f}."
                ),
                importance=4,
                tool="daily_roundup",
            )
        )

    def render_text(self, *, max_stories: Optional[int] = None) -> str:
        lines: List[str] = []
        width = 72
        tagline = TAGLINE_MAJOR if self.major_only else TAGLINE_FULL
        lines.append("=" * width)
        lines.append(PAPER_NAME.center(width))
        lines.append(tagline.center(width))
        lines.append(f"Published {datetime.now().strftime('%Y-%m-%d %H:%M')}".center(width))
        lines.append("=" * width)
        lines.append("")

        stories = self.stories if max_stories is None else self.stories[-max_stories:]
        if not stories:
            lines.append("  No major incidents recorded this run.")
            lines.append("  (Deaths, crimes, violence, and constitutional amendments appear here.)")
            lines.append("")
            lines.append("=" * width)
            return "\n".join(lines)

        by_day: Dict[int, List[Story]] = {}
        for s in stories:
            by_day.setdefault(s.day, []).append(s)

        for day in sorted(by_day.keys()):
            lines.append("-" * width)
            lines.append(f"  DAY {day}")
            lines.append("-" * width)
            day_stories = by_day[day]
            for section in SECTION_ORDER:
                section_stories = [s for s in day_stories if s.section == section]
                if not section_stories:
                    continue
                section_stories.sort(key=lambda s: (-s.importance, s.turn))
                lines.append("")
                lines.append(f"  [{SECTION_TITLES[section].upper()}]")
                for story in section_stories:
                    lines.append(f"  • {story.headline}")
                    lines.append(f"    {story.dateline} | {story.agent_name or '—'}")
                    for para in _wrap(story.body, width - 6):
                        lines.append(f"      {para}")
                    lines.append("")
            lines.append("")

        lines.append("=" * width)
        lines.append(f"  Major stories: {len(self.stories)}")
        lines.append("=" * width)
        return "\n".join(lines)

    def render_html(self) -> str:
        tagline = TAGLINE_MAJOR if self.major_only else TAGLINE_FULL
        by_day: Dict[int, List[Story]] = {}
        for s in self.stories:
            by_day.setdefault(s.day, []).append(s)

        parts = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            f"<title>{escape(PAPER_NAME)}</title>",
            "<style>",
            "body{font-family:Georgia,serif;max-width:820px;margin:2rem auto;background:#1a1a1a;color:#eee;}",
            "header{border-bottom:3px double #c0392b;padding-bottom:1rem;margin-bottom:2rem;text-align:center;}",
            "h1{font-size:2.4rem;margin:0;color:#e74c3c;}",
            ".tagline{font-style:italic;color:#aaa;}",
            ".edition{border-top:1px solid #444;margin-top:2rem;padding-top:1rem;}",
            ".section h2{font-size:1.1rem;color:#e74c3c;text-transform:uppercase;}",
            ".story{margin:1rem 0;padding:1rem;background:#252525;border-left:4px solid #888;}",
            ".story.crime,.story.obituaries{border-left-color:#e74c3c;}",
            ".story.front_page{border-left-color:#c0392b;}",
            ".headline{font-weight:bold;font-size:1.1rem;}",
            ".meta{font-size:0.85rem;color:#888;}",
            ".body{margin:0.5rem 0 0;line-height:1.5;color:#ccc;}",
            ".empty{padding:2rem;text-align:center;color:#888;}",
            "</style></head><body>",
            f"<header><h1>{escape(PAPER_NAME)}</h1>",
            f"<p class='tagline'>{escape(tagline)}</p></header>",
        ]

        if not self.stories:
            parts.append(
                "<p class='empty'>No major incidents recorded. "
                "Deaths, crimes, and constitutional amendments will appear here.</p>"
            )
        else:
            for day in sorted(by_day.keys()):
                parts.append(f"<div class='edition'><h2>Day {day}</h2>")
                day_stories = by_day[day]
                for section in SECTION_ORDER:
                    section_stories = [s for s in day_stories if s.section == section]
                    if not section_stories:
                        continue
                    section_stories.sort(key=lambda s: (-s.importance, s.turn))
                    parts.append(f"<div class='section'><h2>{escape(SECTION_TITLES[section])}</h2>")
                    for story in section_stories:
                        parts.append(f"<article class='story {story.section}'>")
                        parts.append(f"<div class='headline'>{escape(story.headline)}</div>")
                        parts.append(
                            f"<div class='meta'>{escape(story.dateline)}"
                            f"{(' · ' + escape(story.agent_name)) if story.agent_name else ''}</div>"
                        )
                        parts.append(f"<div class='body'>{escape(story.body)}</div>")
                        parts.append("</article>")
                    parts.append("</div>")
                parts.append("</div>")

        parts.append(f"<footer><p>{len(self.stories)} major stories.</p></footer>")
        parts.append("</body></html>")
        return "\n".join(parts)

    def save(self, path: str | Path, *, html: bool = False) -> Path:
        p = Path(path)
        if html or p.suffix.lower() in (".html", ".htm"):
            p.write_text(self.render_html(), encoding="utf-8")
        else:
            p.write_text(self.render_text(), encoding="utf-8")
        return p

    def latest_headlines(self, n: int = 5) -> List[str]:
        if not self.stories:
            return ["No major incidents yet"]
        ranked = sorted(self.stories, key=lambda s: (s.turn, -s.importance))
        return [s.headline for s in ranked[-n:]]


def _is_major_story(story: Story) -> bool:
    if story.tool in MAJOR_TOOLS:
        return True
    if story.importance >= 5:
        return True
    return False


def _wrap(text: str, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    length = 0
    for w in words:
        if length + len(w) + 1 > width and current:
            lines.append(" ".join(current))
            current = [w]
            length = len(w)
        else:
            current.append(w)
            length += len(w) + 1
    if current:
        lines.append(" ".join(current))
    return lines


def _gov_headline(msg: str) -> str:
    if "PASSED" in msg.upper():
        return "CONSTITUTION AMENDED — supermajority vote"
    return "Governance shock"


def _crime_headline(line: str) -> str:
    if "theft" in line.lower():
        return "THEFT — credits stolen"
    if "arson" in line.lower():
        return "ARSON — structure burned"
    if "intimidate" in line.lower():
        return "INTIMIDATION — citizen targeted"
    if "deceive" in line.lower():
        return "DECEPTION — fraud reported"
    if "hoard" in line.lower():
        return "HOARDING — resources seized"
    return "CRIME — public order broken"


def _classify(tool: str, message: str, success: bool) -> Tuple[str, str, int]:
    t = tool.lower()

    if t == "death":
        return "front_page", f"COLLAPSE: {message}", 5
    if t in ("commit_theft", "commit_arson", "intimidate", "deceive_agent", "hoard_resources", "punch"):
        return "crime", message, 5
    if t == "challenge_leader":
        return "society", f"LEADERSHIP CHALLENGED: {message}", 4
    if t == "break_alliance":
        return "society", f"ALLIANCE SHATTERED: {message}", 4
    if t in ("vote_proposal", "propose_constitution", "amend_constitution"):
        return "civic", message, 3
    if t in ("move_north", "move_south", "move_east", "move_west", "rest", "gather_resources"):
        return "skip", message, 0
    return "skip", message, 0


def _format_body(ev: "SimEvent", agent_name: str, sim: "Simulation") -> str:
    agent = sim.agents.get(ev.agent_id)
    loc = ""
    if agent:
        lm = sim.world.landmark_at(agent.x, agent.y)
        loc = f" at {lm.name}" if lm else f" at ({agent.x},{agent.y})"
    role = agent.personality.role if agent else "Citizen"
    return f"{agent_name} ({role}) — {ev.tool}{loc}. {ev.message}"
