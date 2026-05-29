#!/usr/bin/env python3
"""
Long-horizon scheduler — continuous runs with PostgreSQL checkpoints.

No live NYC/news APIs; uses simulated platform_context only.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from config import MAX_TURNS, TICKS_PER_DAY
from llm.settings import LLMSettings
from persistence_factory import create_persistence
from simulation import Simulation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("scheduler")

_stop = False


def _handle_sigterm(*_args) -> None:
    global _stop
    _stop = True
    log.info("Shutdown requested — finishing current turn...")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emergence World long-horizon scheduler")
    p.add_argument("--days", type=int, default=15, help="Run length in sim-days")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--reset", action="store_true", help="Reset database before run")
    p.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL URL (or set DATABASE_URL). Required for multi-week scheduling.",
    )
    p.add_argument("--llm", action="store_true", help="Use LLM for agent decisions")
    p.add_argument("--model", default=None, help="Default LLM model")
    p.add_argument("--llm-delay", type=float, default=0.5, help="Seconds between LLM calls")
    p.add_argument(
        "--tick-interval",
        type=float,
        default=0.0,
        help="Real seconds to sleep after each sim turn (0=fast)",
    )
    p.add_argument(
        "--checkpoint-every",
        type=int,
        default=48,
        help="Log status every N turns (default: 1 sim-day)",
    )
    return p.parse_args()


def main() -> int:
    global _stop
    args = parse_args()
    signal.signal(signal.SIGINT, _handle_sigterm)
    signal.signal(signal.SIGTERM, _handle_sigterm)

    max_turns = args.days * TICKS_PER_DAY
    if max_turns > MAX_TURNS:
        log.error("Max turns %s exceeds limit %s", max_turns, MAX_TURNS)
        return 1

    db = create_persistence(args.database_url)
    llm_settings = LLMSettings.from_env(
        enabled=args.llm,
        model=args.model,
    )
    llm_settings.request_delay_s = args.llm_delay

    sim = Simulation(
        seed=args.seed,
        max_turns=max_turns,
        db=db,
        use_llm=llm_settings.enabled,
        llm_settings=llm_settings,
    )

    if args.reset:
        if hasattr(db, "reset_all"):
            db.reset_all()
        else:
            sim.reset(seed=args.seed)
        sim = Simulation(
            seed=args.seed,
            max_turns=max_turns,
            db=db,
            use_llm=llm_settings.enabled,
            llm_settings=llm_settings,
        )
        log.info("Database reset.")

    backend = "PostgreSQL" if args.database_url or __import__("os").environ.get("DATABASE_URL") else "SQLite"
    mode = "LLM" if sim.orchestrator else "rule-based"
    log.info(
        "Starting scheduler: %s days (%s turns), backend=%s, mode=%s",
        args.days,
        max_turns,
        backend,
        mode,
    )

    while sim.running and sim.turn < sim.max_turns and not _stop:
        sim.step_turn()
        if args.tick_interval > 0:
            time.sleep(args.tick_interval)
        if sim.turn % args.checkpoint_every == 0:
            m = sim.final_metrics()
            day = sim.turn // TICKS_PER_DAY
            log.info(
                "Day %s T%s | alive=%s/10 | crimes=%s | AWI=%.3f | M2=%.4f",
                day,
                sim.turn,
                sim.alive_count(),
                sim.crimes.total,
                m.get("composite_awi", 0),
                m.get("M2_crime_rate", 0),
            )

    if sim.orchestrator:
        log.info("LLM stats: %s", sim.orchestrator.stats())

    log.info("Scheduler finished at turn %s", sim.turn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
