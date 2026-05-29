#!/usr/bin/env python3
"""
Emergence World — local multi-agent emergence simulation.

Inspired by EmergenceAI/Emergence-World (10 citizen personalities).
"""

from __future__ import annotations

import argparse
import sys

from config import DEFAULT_TURNS, MAX_TURNS, TICKS_PER_DAY
from llm.settings import LLMSettings
from persistence_factory import create_persistence
from tool_access import catalog_count
from simulation import Simulation
from tools import TOOLS
from visuals import PYGAME_OK, create_visualizer


def print_banner(*, llm: bool, postgres: bool) -> None:
    store = "PostgreSQL" if postgres else "SQLite"
    brain = "LLM tool-calling" if llm else "rule-based"
    print("=" * 60)
    print("  EMERGENCE WORLD — Local Simulation")
    print(f"  10 agents | 80x80 grid | {catalog_count()}+ tools | {store} | {brain}")
    print("  Weather/news: simulated only (no live APIs)")
    print("=" * 60)


def print_final_report(sim: Simulation) -> None:
    m = sim.final_metrics()
    print("\n" + "=" * 60)
    print("  AWI-STYLE METRICS (end of run)")
    print("=" * 60)
    labels = {
        "population_vitality": "Population Vitality",
        "governance_stability": "Governance Stability",
        "economic_equality": "Economic Equality",
        "social_cohesion": "Social Cohesion",
        "innovation_index": "Innovation Index",
        "conflict_intensity": "Conflict Intensity (lower better)",
        "resource_sustainability": "Resource Sustainability",
        "trust_network_density": "Trust Network Density",
        "cultural_diversity": "Cultural Diversity",
        "composite_awi": "Composite AWI Score",
    }
    for key, label in labels.items():
        val = m.get(key, 0.0)
        bar = "#" * int(val * 30)
        print(f"  {label:32s} {val:6.3f}  {bar}")
    print("=" * 60)
    print(f"  Turns completed: {sim.turn}")
    print(f"  Agents alive:    {sim.alive_count()}/10")
    print(f"  Constitution v{sim.gov.version} | Amendments passed: {sim.gov.amendments_passed}")
    print(f"  Exploration:     {sim.world.exploration_ratio():.1%}")
    print(f"  Tools implemented: {TOOLS.count()} | catalog: {catalog_count()}")
    print(f"  Total crimes:      {sim.crimes.total}")
    if sim.orchestrator:
        print(f"  LLM stats:         {sim.orchestrator.stats()}")
    print("=" * 60)


def run_headless(sim: Simulation) -> None:
    print(f"Running headless for {sim.max_turns} turns...")
    while sim.running and sim.turn < sim.max_turns:
        sim.run_batch(10)
        if sim.turn % 50 == 0:
            m = sim.final_metrics()
            print(
                f"  T{sim.turn:4d} | alive={sim.alive_count()} "
                f"| AWI={m['composite_awi']:.3f} "
                f"| cohesion={m['social_cohesion']:.3f} "
                f"| conflict={m['conflict_intensity']:.3f}"
            )
    print_final_report(sim)


def run_visual(sim: Simulation) -> None:
    backend = "pygame" if PYGAME_OK else "matplotlib (fallback)"
    print(f"Starting visual mode ({backend})...")
    print("Controls: Space=pause, +/-=speed, Tab=cycle inspect, Q/Esc=quit")
    viz = create_visualizer(sim)
    try:
        while sim.running and sim.turn < sim.max_turns:
            if not viz.render():
                break
    finally:
        viz.close()
    print_final_report(sim)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emergence World local simulation")
    p.add_argument("--turns", type=int, default=None, help="Simulation turns (sim-hours)")
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Season-style run length in days (1 day={TICKS_PER_DAY} turns)",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed")
    p.add_argument("--headless", action="store_true", help="No GUI — fast batch run")
    p.add_argument("--reset", action="store_true", help="Reset SQLite database")
    p.add_argument("--no-visual", action="store_true", help="Alias for headless")
    p.add_argument("--llm", action="store_true", help="Use LLM API for agent decisions")
    p.add_argument("--model", default=None, help="LLM model (or EMERGENCE_LLM_MODEL)")
    p.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL URL (or DATABASE_URL env); default SQLite",
    )
    p.add_argument(
        "--llm-delay",
        type=float,
        default=0.0,
        help="Seconds between LLM calls (rate limit)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    llm_settings = LLMSettings.from_env(enabled=args.llm, model=args.model)
    llm_settings.request_delay_s = args.llm_delay
    use_postgres = bool(
        args.database_url
        and args.database_url.startswith(("postgres://", "postgresql://"))
    ) or bool(__import__("os").environ.get("DATABASE_URL", "").startswith("postgres"))

    print_banner(llm=llm_settings.enabled, postgres=use_postgres)

    if args.days is not None:
        max_turns = args.days * TICKS_PER_DAY
    elif args.turns is not None:
        max_turns = args.turns
    else:
        max_turns = DEFAULT_TURNS

    if max_turns < 1 or max_turns > MAX_TURNS:
        print(f"Turns must be 1..{MAX_TURNS}", file=sys.stderr)
        return 1

    db = create_persistence(args.database_url)
    sim = Simulation(
        seed=args.seed,
        max_turns=max_turns,
        db=db,
        use_llm=llm_settings.enabled,
        llm_settings=llm_settings,
        database_url=args.database_url,
    )
    if args.reset:
        sim.reset(seed=args.seed)
        print("Database reset.")
    if args.llm and not llm_settings.enabled:
        print(
            "Warning: --llm set but no API key. Set OPENAI_API_KEY or EMERGENCE_LLM_API_KEY.",
            file=sys.stderr,
        )

    headless = args.headless or args.no_visual
    if headless:
        run_headless(sim)
    else:
        run_visual(sim)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
