# CLAUDE.md — CFB Agent Project Briefing

> This file is read by Claude Code at the start of every session.
> Update at the end of each phase before committing.

---

## Project Overview

**Name:** CFB Agent
**Purpose:** College football betting prediction agent — end-to-end AI/data engineering portfolio project and planned subscription product targeting CFB bettors.
**Target users:** CFB bettors who want model-backed win probability, line value flags, and verified pick tracking (CLV as primary credibility metric).
**Repo:** `github.com/Jeff-Hawkins/cfb-agent`
**Local path:** `~/cfb-agent`

---

## Current Stack

| Layer | Technology |
|---|---|
| Language | Python 3.x (Anaconda) |
| ML Model | LightGBM |
| Agent Orchestrator | LangGraph + Groq `llama-3.3-70b-versatile` (temp=0.1) |
| Database | Supabase (PostgreSQL) — project `cfb-agent`, East US N.Virginia, free plan |
| ORM / DB Layer | SQLAlchemy + psycopg2-binary |
| Data | College Football Data API (free tier) |
| Backend | FastAPI — deployed on Railway |
| Frontend (current) | Streamlit (deployed on Streamlit Cloud) |
| Frontend (planned) | React + Vite + Tailwind + shadcn/ui — Phase 4 |
| Hosting | Railway (backend), Vercel (frontend, planned) |
| CI/CD (planned) | GitHub Actions |

---

## Repo Structure

```
cfb-agent/
├── data/
├── tools/
│   └── stats_fetcher.py
├── db/
│   ├── database.py
│   └── schema.py
├── models/
│   ├── win_probability.py
│   ├── preseason_ratings.py
│   └── saved/
│       ├── win_prob_model.pkl
│       └── feature_cols.pkl
├── agent/
│   └── orchestrator.py
├── backend/                        # FastAPI — deployed on Railway
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── nixpacks.toml
│   ├── db/                         # copied from root db/ for Railway
│   │   ├── database.py
│   │   └── schema.py
│   ├── models/                     # copied from root models/ for Railway
│   │   ├── win_probability.py
│   │   ├── preseason_ratings.py
│   │   └── saved/
│   └── routers/
│       ├── __init__.py
│       ├── matchup.py
│       ├── rankings.py
│       └── games.py
├── tests/
│   └── test_api.py
├── app.py                          # Streamlit UI (legacy)
├── main.py
├── .env                            # Never commit — credentials here
└── CLAUDE.md                       # This file
```

> Phase 4 will add `/frontend` — repo becomes full mono-repo.

---

## Completed Phases

### Phase 1A (commit `6eeb926`) ✅
- SQLite → Supabase (PostgreSQL) migration
- 4-test suite passing
- 5-year historical data live

### Phase 1B (commit `6297c92`) ✅
- Added tables: `elo_ratings`, `talent`, `advanced_stats`, `drives`, `pregame_wp`
- `neutral_site` field confirmed
- Weather deferred — Phase 7
- 9 tests passing

### Phase 2 (commit `5383438`) ✅
- LightGBM retrained — `spread_diff` removed (feature leakage)
- 21 features: SP+ differentials, 3yr recruiting avg, returning production, portal net, coaching signals, recency weighting, home field, `elo_diff`, `talent_diff`, `neutral_site`
- Holdout accuracy: **78.22%** | Brier: **0.1569**
- 10 tests passing

### Phase 3 (commit `f893849`) ✅
- FastAPI backend complete
- Endpoints: `GET /health`, `GET /matchup`, `GET /rankings`, `GET /games`
- `backend/routers/`: `matchup.py`, `rankings.py`, `games.py`
- `tests/test_api.py`

### Railway Deploy ✅
- Live URL: `https://cfb-agent-production.up.railway.app`
- Dockerfile used (nixpacks could not resolve libgomp)
- `libgomp1` installed via apt in Dockerfile for LightGBM
- `sqlalchemy` and `psycopg2-binary` in `backend/requirements.txt`
- `DATABASE_URL` uses Supabase Transaction Pooler (port 6543, IPv4 compatible)
- `backend/db/` and `backend/models/` copied into backend for Railway self-containment
- All endpoints tested live:
  - `/health` → `{"status":"ok"}`
  - `/rankings` → 136 FBS teams, `nationalAverages` filtered, `fillna("")` applied
  - `/matchup?home=Georgia&away=Ohio+State&season=2025` → win probabilities
  - `/games?week=1` → 2025 regular season FBS games by week

---

## Current Phase

### Phase 4 — React + Tailwind + shadcn/ui Frontend 🔄

**Goal:** Build a production-quality React frontend consuming the live Railway backend.

**Design:**
- Theme: Dark + Gold (`#0a0a0a` bg, `#C9A84C` gold, `#111111` cards, `#FFFFFF` text)
- Font: Inter
- Mobile responsive
- Plain JSX only — no TypeScript

**Pages:**
- **Schedule Page** — 2025 games by week (week selector), clickable game cards showing win probability on click. FCS opponents labeled. Swaps to 2026 when data available.
- **Power Rankings Page** — sortable table of 136 FBS teams, conference filter, top 25 gold left border

**Components:**
- `Navbar.jsx` — tabs: Schedule | Power Rankings
- `WinProbGauge.jsx` — Recharts RadialBarChart
- `ConfidenceBadge.jsx` — toss-up/lean/moderate/strong
- `GameCard.jsx` — clickable game card

**API client (`src/api/client.js`):**
- `getGames(week)` → `GET /games?week=X`
- `getMatchup(home, away, season)` → `GET /matchup`
- `getRankings()` → `GET /rankings`

**Stack:** React + Vite + Tailwind + shadcn/ui + Recharts + react-router-dom
**Env var:** `VITE_API_URL=https://cfb-agent-production.up.railway.app`
**Lives in:** `/frontend`
**Deploy:** Vercel (root `/frontend`, build `npm run build`, output `dist`)

---

## Upcoming Phases

| Phase | Description |
|---|---|
| 4.5 | Pick review UI, value flag logic, Claude Sonnet draft pipeline |
| 5 | Deploy + swap Groq → Claude Sonnet |
| 6 | Bayesian updating + Platt scaling |
| 7 | Line value engine + spread_diff + weather |
| Launch | Late August 2026 |

---

## Conventions & Non-Negotiables

- **Tests required** before any function ships
- **Docstrings on every module**
- **Never hardcode credentials** — `.env` locally, Railway/Vercel dashboards in prod
- **No Co-Authored-By in commits** — never
- **backend/ is self-contained** — any root module used by API must be copied into `backend/`
- **Honest model framing** — surface known limits, don't hide them

---

## Model Details

### Win Probability
- LightGBM | 21 features | Train 2021–2024 | Test 2025
- Accuracy: 78.22% | Brier: 0.1569
- Known limits: no injury/rankings/momentum data

### Preseason Composite
- 72.87% backtest accuracy (2024)
- Weights: SP+ 25%, Recruiting 20%, Returning prod 20%, Portal 20%, Coach 15%
- 136 FBS teams rated for 2026

---

## Deferred Decisions

| Item | Phase |
|---|---|
| `spread_diff` as live feature | 7 |
| Platt scaling | 6 |
| Weather | 7 |
| Groq → Claude Sonnet | 5 |
| Bayesian updating | 6 |
| 2026 schedule (swap from 2025 demo) | When CFB API publishes it |

---

## Railway Deploy Notes

- Root directory: `backend`
- Dockerfile used — do NOT switch to nixpacks
- Start command: blank (Dockerfile CMD handles it)
- Do NOT set PORT variable in Railway dashboard
- New backend dependencies → `backend/requirements.txt`
- New root modules used by backend → copy into `backend/`

---

## Environment Variables

**Local `.env`**
```
SUPABASE_URL=
SUPABASE_KEY=
CFB_API_KEY=
GROQ_API_KEY=
DATABASE_URL=postgresql://postgres.loditcbewcpangrqgahd:[password]@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

**Railway dashboard**
```
DATABASE_URL=postgresql://postgres.loditcbewcpangrqgahd:[password]@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

**Vercel dashboard (Phase 4)**
```
VITE_API_URL=https://cfb-agent-production.up.railway.app
```

---

## Claude Code Workflow

- Design + spec full phase in chat first
- Produce single structured batch prompt for Claude Code
- Claude Code executes full module in one session
- Return to chat to review, commit, plan next phase
- Never iterate one function at a time
- No Co-Authored-By in commits

---

*Last updated: Railway deploy complete. Phase 4 (React frontend) active.*
