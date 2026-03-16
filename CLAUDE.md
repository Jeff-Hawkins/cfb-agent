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
| Database | Supabase (PostgreSQL) — project `cfb-agent`, East US N.Virginia |
| ORM / DB Layer | SQLAlchemy |
| Data | College Football Data API (free tier) |
| Backend | FastAPI — deployed Phase 3 ✅ |
| Frontend (current) | Streamlit (deployed on Streamlit Cloud) |
| Frontend (planned) | React + Tailwind + shadcn/ui + Vite — Phase 4 |
| Hosting (planned) | Railway (backend), Vercel (frontend) |
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
│   └── saved/               # win_prob_model.pkl, feature_cols.pkl
├── backend/                 # Phase 3 ✅
│   ├── main.py              # FastAPI app, CORS, /health
│   ├── routers/
│   │   ├── matchup.py       # GET /matchup?home=X&away=Y&season=N
│   │   └── rankings.py      # GET /rankings
│   └── requirements.txt
├── agent/
│   └── orchestrator.py
├── tests/
│   ├── test_database.py     # 10 tests
│   └── test_api.py          # 4 tests
├── app.py                   # Streamlit UI
├── main.py
├── .env                     # Never commit — credentials here
└── CLAUDE.md                # This file
```

---

## Completed Phases

### Phase 1A (commit `6eeb926`) ✅
- SQLite → Supabase (PostgreSQL) migration
- 4-test suite passing
- 5-year historical data live

### Phase 1B (commit `6297c92`) ✅
- Added tables: `elo_ratings`, `talent`, `advanced_stats`, `drives`, `pregame_wp`
- `neutral_site` field confirmed
- Weather integration deferred — Phase 7
- 9 tests passing

### Phase 2 (commit `5383438`) ✅
- LightGBM retrained — `spread_diff` **removed** (feature leakage)
- 22 features: SP+ differentials, 3yr recruiting avg, returning production (`percentPPA`) with conference multipliers, portal net with eligibility weighting, coaching signals, recency weighting (2025=1.0 → 2021=0.2), home field, `elo_diff`, `talent_diff`, `neutral_site`
- Holdout accuracy: **78.22%** | Brier score: **0.1569**
- Calibration solid 0.3–0.7; slight overconfidence >0.9
- `betting_lines` flat schema: one consensus row per game, averaged across DraftKings/Bovada/ESPN Bet
- 10 tests passing

### Phase 3 (commit `f893849`) ✅
- FastAPI backend live at `http://127.0.0.1:8000`
- `GET /health` — liveness check
- `GET /matchup?home=X&away=Y&season=N` — win probability via LightGBM
- `GET /rankings` — 2026 preseason composite ratings, all 137 FBS teams, with conference via sp_ratings join
- Model paths use `os.path.dirname(__file__)` — safe to run from any working directory
- 4 API tests passing (14 total)
- Deploy target: Railway (root `/backend`)

---

## Current Phase

### Phase 4 — React Frontend 🔄

**Goal:** Replace Streamlit with a React + Tailwind + shadcn/ui + Vite frontend that consumes the Phase 3 FastAPI backend.

**Planned views:**
- Matchup lookup (home vs. away win probability)
- Rankings table (2026 preseason composite, all 137 teams)
- Picks tracker (ATS/ROI/CLV dashboard)
- Games feed (upcoming games with model predictions)

**Frontend will live in:** `/frontend` (mono-repo)
**Deploy target:** Vercel

---

## Upcoming Phases (Roadmap)

| Phase | Description | Target |
|---|---|---|
| 4 | React + Tailwind + shadcn/ui frontend | Next |
| 4.5 | Pick review UI, value flag logic, Claude Sonnet draft pipeline | After Phase 4 |
| 5 | Deploy + swap Groq → Claude Sonnet as agent LLM | After Phase 4 |
| 6 | Bayesian in-season updating + Platt scaling calibration | Mid-season |
| 7 | Line value engine + `spread_diff` re-introduced + weather integration | Pre-launch |
| Launch | Target late August 2026 | — |

---

## Conventions & Non-Negotiables

- **Tests are required** before any function ships — no exceptions
- **Docstrings on every module** — always
- **Never hardcode credentials** — all secrets via `.env` and Railway env vars
- **No spaghetti** — clean separation of concerns; DB logic in `db/`, model logic in `models/`, agent logic in `agent/`
- **Honest model framing** — known limits (no injury/rankings/momentum data) are surfaced as features, not hidden
- **Commit messages:** Never add Co-Authored-By lines

---

## Model Details

### Win Probability Model
- **Algorithm:** LightGBM
- **Features (22):** SP+ differentials, 3yr recruiting avg, returning production with conference multipliers, portal net with eligibility weighting, coaching signals, recency weighting, home field, `elo_diff`, `talent_diff`, `neutral_site`
- **Train:** 2021–2024 | **Test:** 2025
- **Holdout accuracy:** 78.22% | **Brier:** 0.1569
- **Known limits:** No injury data, no rankings/momentum signals
- **Params:** `num_leaves=31`, `min_child_samples=20`, `reg_alpha/lambda=0.1`, `subsample=0.8`

### Preseason Composite Ratings
- **Backtest accuracy (2024):** 72.87%
- **Weights:** SP+ 25%, Recruiting 20%, Returning production 20%, Portal net 20%, Coach effectiveness 15%
- **Coverage:** 2026 ratings live for all 137 FBS teams

---

## Deferred Decisions (Do Not Implement Early)

| Item | Deferred To |
|---|---|
| `spread_diff` as live feature | Phase 7 (line value engine) |
| Platt scaling / calibration fix | Phase 6 |
| Weather integration | Phase 7 |
| Groq → Claude Sonnet swap | Phase 5 |
| Bayesian in-season updating | Phase 6 |

---

## Environment Variables (Never Commit)

```
SUPABASE_URL=
SUPABASE_KEY=
CFB_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=       # Needed Phase 5+
```

---

## Monetization Context

- **Strategy:** Content-first → audience → subscriptions
- **CLV (Closing Line Value)** is the primary credibility metric — not raw accuracy
- **Pick tracking** feeds the public CLV dashboard — subscriber magnet
- **Content automation:** Weekly Claude Sonnet drafts LinkedIn/X posts for Jeff's review (Season 1 = human-reviewed, not fully automated)
- **Launch target:** Late August 2026 (before CFB season kickoff)

---

## Claude Code Workflow

- Design + spec full phase in chat first
- Produce a single structured batch prompt for Claude Code
- Claude Code executes full module in one session
- Return to chat to review, commit, plan next phase
- **Never iterate one function at a time** — full module specs only

---

*Last updated: Phase 3 complete. Phase 4 (React frontend) next.*
