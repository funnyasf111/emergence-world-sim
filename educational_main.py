#!/usr/bin/env python3
"""Educational Emergence World variant (emergence_sim package, no SQLite)."""

from __future__ import annotations

import argparse

from emergence_sim.engine import EmergenceSimulation, SimulationConfig
from emergence_sim.visualize import create_visualizer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Educational Emergence World simulation (10 agents, visual emergence)."
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    p.add_argument("--fps", type=int, default=10, help="Frames per second")
    p.add_argument("--steps", type=int, default=2, help="Simulation ticks per frame")
    p.add_argument("--days", type=int, default=15, help="Simulated days (15 = Season 1 scale)")
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run without GUI; print final metrics summary",
    )
    p.add_argument(
        "--backend",
        choices=("auto", "pygame", "matplotlib"),
        default="auto",
        help="Visualization backend",
    )
    return p.parse_args()


def run_headless(sim: EmergenceSimulation) -> None:
    while sim.step():
        pass
    snap = sim.metrics.latest
    print("\n=== Emergence World — Headless Run Complete ===")
    if snap:
        for k, v in snap.as_dict().items():
            print(f"  {k}: {v}")
    print(f"\nAlive: {[a.name for a in sim.alive_agents()]}")
    print(f"Events ({len(sim.world.event_log)}):")
    for ev in sim.world.event_log[-10:]:
        print(f"  {ev}")


def main() -> None:
    args = parse_args()
    max_ticks = args.days * 48
    sim = EmergenceSimulation(
        SimulationConfig(seed=args.seed, max_ticks=max_ticks),
    )

    if args.headless:
        run_headless(sim)
        return

    if args.backend == "matplotlib":
        from emergence_sim.visualize import MatplotlibVisualizer

        MatplotlibVisualizer().run(sim, steps_per_frame=args.steps, fps=args.fps)
    elif args.backend == "pygame":
        from emergence_sim.visualize import HAS_PYGAME, PygameVisualizer

        if not HAS_PYGAME:
            raise SystemExit("pygame not installed. pip install pygame")
        PygameVisualizer().run(sim, steps_per_frame=args.steps, fps=args.fps)
    else:
        create_visualizer().run(sim, steps_per_frame=args.steps, fps=args.fps)


if __name__ == "__main__":
    main()
