#!/usr/bin/env python3
"""
Emergence World — local multi-agent emergence simulation.

Inspired by EmergenceAI/Emergence-World (10 citizen personalities).
"""

from __future__ import annotations

import argparse
import sys

from config import DEFAULT_TURNS, MAX_TURNS
from simulation import Simulation
from tools import TOOLS
from visuals import PYGAME_OK, create_visualizer


def print_banner() -> None:
    print("=" * 60)
    print("  EMERGENCE WORLD — Local Simulation")
    print("  10 agents | 80x80 grid | governance | SQLite persistence")
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
    print(f"  Tools available: {TOOLS.count()}")
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
    p.add_argument("--turns", type=int, default=DEFAULT_TURNS, help="Simulation turns (hours)")
    p.add_argument("--seed", type=int, default=42, help="RNG seed")
    p.add_argument("--headless", action="store_true", help="No GUI — fast batch run")
    p.add_argument("--reset", action="store_true", help="Reset SQLite database")
    p.add_argument("--no-visual", action="store_true", help="Alias for headless")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print_banner()

    if args.turns < 1 or args.turns > MAX_TURNS:
        print(f"Turns must be 1..{MAX_TURNS}", file=sys.stderr)
        return 1

    sim = Simulation(seed=args.seed, max_turns=args.turns)
    if args.reset:
        sim.reset(seed=args.seed)
        print("Database reset.")

    headless = args.headless or args.no_visual
    if headless:
        run_headless(sim)
    else:
        run_visual(sim)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
