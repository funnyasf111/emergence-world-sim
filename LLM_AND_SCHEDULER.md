# LLM Orchestration + PostgreSQL + Long-horizon Scheduler

Implements steps **1, 2, and 4** from the platform roadmap — **not** live NYC/news APIs (step 3 stays simulated in `platform_context.py`).

## 1. LLM tool-calling (model-agnostic)

Agents choose tools via an **OpenAI-compatible** chat API (`/v1/chat/completions` + function tools).

Works with:

- OpenAI
- Any OpenAI-compatible proxy (LM Studio, vLLM, Azure OpenAI, etc.)

### Setup

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY only (no news/weather API keys needed)

export OPENAI_API_KEY=sk-...
export EMERGENCE_LLM_MODEL=gpt-4o-mini   # optional
```

### Run

```bash
# Headless Season 1 with LLM brains (slow — one API call per agent per turn)
python main.py --headless --days 15 --reset --llm --llm-delay 0.3

# Rule-based fallback if API fails (automatic per agent per turn)
```

Per-agent model override:

```bash
export EMERGENCE_MODEL_ANCHOR=gpt-4o
export EMERGENCE_MODEL_KADE=gpt-4o-mini
```

## 2. PostgreSQL persistence

For multi-day scheduling without losing state:

```bash
docker compose up -d
export DATABASE_URL=postgresql://emergence:emergence@localhost:5432/emergence_world
pip install 'psycopg[binary]'
```

## 4. Long-horizon scheduler

```bash
# Fast checkpointed run (PostgreSQL + optional LLM)
python scheduler.py --days 15 --reset --database-url "$DATABASE_URL"

# Real-time pacing: 1 real second per sim-hour
python scheduler.py --days 15 --tick-interval 1.0 --database-url "$DATABASE_URL"

# Full stack: Postgres + LLM
python scheduler.py --days 15 --reset --llm --model gpt-4o-mini \
  --database-url "$DATABASE_URL" --llm-delay 0.5
```

Logs every sim-day (48 turns): population, crimes, AWI.

## What is NOT included (by design)

- Live NYC weather APIs
- Live news / internet APIs  
- React 3D client  
- Hosted multi-week cloud orchestration  

Weather and headlines remain **simulated** in `platform_context.py`.

## Architecture

```
main.py / scheduler.py
    → Simulation
        → AgentOrchestrator (llm/)  OR  choose_action() rules
        → TOOLS.execute()
        → Persistence (SQLite) OR PostgresPersistence
```

## Cost warning

`--days 15 --llm` ≈ **720 turns × 10 agents = 7,200 API calls**. Use `--days 1` for testing, or `--llm-delay` to avoid rate limits.
