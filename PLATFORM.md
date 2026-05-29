# Emergence World Platform Alignment

This document maps the **local educational simulator** to the [Emergence AI research platform](https://www.emergence.ai/blog/emergence-world-a-laboratory-for-evaluating-long-horizon-agent-autonomy) and [EmergenceAI/Emergence-World](https://github.com/EmergenceAI/Emergence-World).

## What this repo implements (local)

| Platform feature | Local implementation |
|------------------|----------------------|
| 10 distinct citizens | `personalities.py` — Anchor, Anvil, Blackbox, Flora, Genome, Horizon, Kade, Lovely, Mira, Spark |
| Shared spatial world | 80×80 grid, **40+ landmarks** (`world.py`) |
| 120+ tools (3-tier) | `tool_access.py` catalog; **~45 handlers** in `tools.py` with aliases + gating |
| Location-gated tools | Town Hall voting, library research, police complaints, Victory Arch pitches, etc. |
| 70% governance supermajority | `PASS_THRESHOLD = 0.70` in `config.py` |
| Energy / survival pressure | Per-turn decay + action costs; starvation at 0 energy |
| Prohibited actions | Theft, intimidation, arson, deception, hoarding — tracked in `crime_stats.py` |
| Triple memory | Episodic (`episodic_memory`), diary (`diary`), relationship labels (`relationship_labels`) |
| Persistent state | SQLite (`persistence.py`) |
| NYC time / weather / news | `platform_context.py` (simulated, no API keys) |
| AWI-style metrics | M1–M9 fields in `metrics.py` |
| 15-day Season 1 scale | `python main.py --days 15` (48 turns/day) |
| Visual observation | Pygame + matplotlib fallback (`visuals.py`) |

## What requires the full Emergence stack (not in this repo)

| Production feature | Notes |
|--------------------|--------|
| Frontier LLM reasoning | Local agents use **personality-weighted rules**, not Claude/Gemini/Grok APIs |
| React Three Fiber 3D world | Local uses 2D grid visualization |
| PostgreSQL + FastAPI + WebSockets | Local uses SQLite + CLI |
| Live NYC APIs / internet | Local uses **simulated** headlines and weather |
| 120+ fully unique tool implementations | Local **catalogs 120+** names; many chain to core handlers |
| Weeks of cloud orchestration | Local runs complete in minutes (`--headless`) |
| Cross-vendor parallel worlds | Run multiple seeds/models yourself; no hosted replay |

## Run like Season 1 (15 days)

```bash
cd /home/fuckyou/Projects/emergence-sim
pip install -r requirements.txt
python main.py --headless --days 15 --seed 42 --reset
```

Watch for blog-style dynamics:

- **Crime curves** — `M2_crime_rate`, `sim.crimes.total`
- **Population** — `M1_population`, agents alive at day 16
- **Governance** — proposals every 40 turns, 70% pass threshold
- **Tool discovery** — agents blocked until they reach Town Hall / Library / etc.
- **Social fabric** — alliances, rivals, relationship labels

## Educational variant

`emergence_sim/` + `educational_main.py` — lighter 32×32 package without SQLite (useful for teaching).

## Citation

Emergence World — Emergence AI. Non-commercial research use: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
