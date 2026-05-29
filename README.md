# Emergence World — Local Simulation

Educational multi-agent simulation inspired by [EmergenceAI/Emergence-World](https://github.com/EmergenceAI/Emergence-World): 10 distinct citizen personalities, an 80×80 grid with 25 landmarks, governance, economy, relationships, and real-time visuals.

## Requirements

- Python 3.11+
- numpy, matplotlib, networkx, pygame

## Setup

```bash
cd ~/Projects/emergence-world-sim
python3 -m venv .venv          # if this fails: sudo apt install python3-venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Debian without `python3-venv`, either install that package or use:

```bash
pip3 install --break-system-packages -r requirements.txt
```

## Run

**Visual mode (default, 500 turns):**

```bash
python main.py
```

**Headless (fast, prints AWI metrics):**

```bash
python main.py --headless --turns 500
```

**Season 1 scale (15 sim-days ≈ blog experiment horizon):**

```bash
python main.py --headless --days 15 --seed 42 --reset
```

**Options:**

```bash
python main.py --turns 1000 --seed 7 --reset
```

See [PLATFORM.md](PLATFORM.md) for alignment with the Emergence AI research platform.

### In-sim controls (Pygame)

| Key | Action |
|-----|--------|
| Space | Pause / resume |
| `+` / `-` | Speed up / down |
| Tab | Cycle inspected agent |
| Q / Esc | Quit and print metrics |

## What to watch for (emergence)

- **Clustering** — agents gathering at landmarks (Market, Commons, Forge)
- **Alliances** — persistent dyads in the relationship graph (green edges)
- **Inequality** — credit spread widening under Risk / Trade roles
- **Governance** — constitution amendments proposed and voted every ~40 turns
- **Conflict** — challenge/mediate loops between high-credit and mediator agents

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | CLI entry, run loop |
| `simulation.py` | Turn engine |
| `agents.py` | Agents + relationship graph |
| `tools.py` | 32 tool functions |
| `world.py` | Grid, landmarks, resources |
| `governance.py` | Constitution & voting |
| `metrics.py` | 9 AWI-style end metrics |
| `visuals.py` | Pygame UI + matplotlib fallback |
| `persistence.py` | SQLite state |
| `personalities.py` | Emergence World roster |

State is stored in `emergence_world.db` in the project directory.

## Educational variant (`emergence_sim/`)

A lighter, package-based variant (32×32 grid, no SQLite) lives under `emergence_sim/`:

```bash
python educational_main.py
python educational_main.py --headless --seed 42 --days 15
```

| Module | Purpose |
|--------|---------|
| `emergence_sim/engine.py` | Simulation loop |
| `emergence_sim/agents.py` | 10 profiles + trust graph |
| `emergence_sim/visualize.py` | Pygame + matplotlib fallback |

## AWI metrics (end of run)

1. Population Vitality  
2. Governance Stability  
3. Economic Equality  
4. Social Cohesion  
5. Innovation Index  
6. Conflict Intensity  
7. Resource Sustainability  
8. Trust Network Density  
9. Cultural Diversity  
+ Composite AWI score

## Attribution

Citizen names, roles, and drives are based on **Emergence World** by Emergence AI ([CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)).
