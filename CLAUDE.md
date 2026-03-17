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
| Frontend | React + Vite + Tailwind + shadcn/ui — deployed on Vercel |
| Auth | Supabase Auth (email/password) |
| Email | SendGrid |
| CI/CD | GitHub Actions |

---

## Repo Structure

```
cfb-agent/
├── data/
├── tools/
│   └── stats_fetcher.py
├── db/
│   ├── database.py
│   ├── schema.py
│   └── migrations/
│       ├── 002_picks_table.sql
│       └── 003_pick_explanations.sql  # Phase 5 ✅
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
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── matchup.py
│   │   ├── rankings.py
│   │   ├── games.py
│   │   ├── picks.py                # Phase 4.5
│   │   └── explanations.py         # Phase 5
│   ├── tools/                      # copied from root tools/ for Railway
│   │   ├── explanation_generator.py  # Phase 5
│   │   └── platt_scaler.py           # Phase 5
│   └── services/
│       └── notifications.py        # Phase 4.5 — SendGrid email
├── frontend/                       # React frontend — deployed on Vercel
│   ├── src/
│   │   ├── api/client.js
│   │   ├── lib/
│   │   │   └── supabase.js         # Phase 4.5 — Supabase client
│   │   ├── components/
│   │   │   ├── Navbar.jsx          # Phase 4.5 — auth-aware
│   │   │   ├── ProtectedRoute.jsx  # Phase 4.5
│   │   │   ├── WinProbGauge.jsx
│   │   │   ├── ConfidenceBadge.jsx
│   │   │   ├── GameCard.jsx
│   │   │   └── LoadingSkeleton.jsx
│   │   ├── pages/
│   │   │   ├── SchedulePage.jsx
│   │   │   ├── RankingsPage.jsx
│   │   │   ├── LoginPage.jsx       # Phase 4.5
│   │   │   └── admin/
│   │   │       ├── PendingPicksPage.jsx   # Phase 4.5
│   │   │       └── PickHistoryPage.jsx    # Phase 4.5
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── .env
│   ├── vercel.json                 # SPA rewrite rule
│   └── vite.config.js
├── .github/
│   └── workflows/
│       └── weekly_pipeline.yml     # Phase 4.5 — Tue flag + Sun outcomes
├── tests/
│   ├── test_api.py
│   ├── test_picks.py               # Phase 4.5 — 15 tests
│   ├── test_platt.py               # Phase 5
│   ├── test_explanation_generator.py  # Phase 5
│   └── test_explanations_api.py    # Phase 5
├── app.py                          # Streamlit UI (legacy)
├── main.py
├── .env                            # Never commit — credentials here
└── CLAUDE.md                       # This file
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

### Phase 4 (commit `eb715ed`) ✅
- React + Vite + Tailwind frontend built
- Pages: SchedulePage (games by week, win prob on click), RankingsPage (sortable, conference filter)
- Components: Navbar, GameCard, WinProbGauge, ConfidenceBadge, LoadingSkeleton
- Vercel deploy pending (env vars needed)

### Phase 5 (commit `93cd21d`) ✅
- **Platt scaling** — `models/platt_scaler.py` + `backend/models/saved/platt_scaler.joblib`
  - `CalibratedClassifierCV(method='sigmoid')` trained on LightGBM outputs
  - `calibrate_probability(raw_prob)` applied after every prediction
  - `predict_win_probability` now returns `{win_prob, raw_win_prob}` dict; `MODEL_VERSION = "2.0.0"`
- **AI Explanations** — `tools/explanation_generator.py` (+ backend copy)
  - `build_feature_snapshot()` — queries all 6 data tables, returns labelled feature dict
  - `generate_explanation_short()` / `generate_explanation_full()` — Groq `llama-3.3-70b-versatile` at temp=0.1
  - `generate_and_store_explanation()` — upserts into `pick_explanations` table
  - `FEATURE_DESCRIPTIONS` map covers all 21 model features with plain-English labels
- **`/explanations` router** — `GET /explanations/{pick_id}` (public), `POST /explanations/generate/{pick_id}` (admin)
- **Pick approval** — triggers `generate_and_store_explanation` as FastAPI BackgroundTask on approve
- **`pick_explanations` table** — `db/migrations/003_pick_explanations.sql` ✅ Run in Supabase
- **Frontend updates** — PendingPicksPage shows AI Analysis section + raw win prob; `featureDescriptions.js` shared map
- **45 tests passing** — `test_platt.py`, `test_explanation_generator.py`, `test_explanations_api.py`
- Key fix: `backend/tools/` is resolved via `sys.path` — always apply fixes to both root and backend copies

### Phase 4.5 (commits `abc05a3`, `1ca521b`, `6f5925f`) ✅
- **picks table** — `db/migrations/002_picks_table.sql` — run against Supabase ✅
- **`/picks` router** — flag, pending, approve, reject, approved, update-outcomes
  - Flag logic: win_prob >= 0.65 AND model_spread_diff >= 3.0
  - model_implied_spread = (home_win_prob - 0.5) * 28
  - Confidence labels: Lean (65–74%), Moderate (75–84%), Strong (85%+)
  - All POST endpoints require Bearer token (ADMIN_API_KEY)
  - Performance fix: model + all 6 data tables pre-loaded once per request (not per game)
- **SendGrid notifications** — `backend/services/notifications.py`
- **Admin UI** — LoginPage, ProtectedRoute, PendingPicksPage, PickHistoryPage
- **Auth-aware Navbar** — shows Admin/History/Logout when session active
- **GitHub Actions** — `weekly_pipeline.yml`: Tue 11PM ET flag-picks, Sun 10AM ET update-outcomes
- **19 tests passing** — `tests/test_picks.py`
- **Tested live**: `/picks/flag?season=2025&week=1` → `{"flagged": 38}` ✅

### Railway Deploy ✅
- Live URL: `https://cfb-agent-production.up.railway.app`
- Dockerfile used (nixpacks could not resolve libgomp)
- `libgomp1` installed via apt in Dockerfile for LightGBM
- `sqlalchemy` and `psycopg2-binary` in `backend/requirements.txt`
- `DATABASE_URL` uses Supabase Transaction Pooler (port 6543, IPv4 compatible)
- `backend/db/` and `backend/models/` copied into backend for Railway self-containment
- All endpoints tested live

---

## Current Phase

### Next: Phase 6 — Bayesian Updating + Vercel Deploy 🔄

**Pending manual steps:**
1. Run `db/migrations/003_pick_explanations.sql` in Supabase SQL Editor
2. Vercel deploy (if not yet done):
   - Root directory: `frontend` | Build: `npm run build` | Output: `dist`
   - Env vars: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_ADMIN_API_KEY`
3. Railway secrets: `SENDGRID_API_KEY`, `NOTIFY_EMAIL` (ADMIN_API_KEY already set)
4. GitHub Actions secrets: `RAILWAY_BACKEND_URL`, `ADMIN_API_KEY`

---

## Upcoming Phases

| Phase | Description | Target |
|---|---|---|
| 6 | Bayesian in-season updating + model recalibration | v1 |
| 7 | Line value engine + spread_diff reintroduction + weather + power ratings pipeline (SP+ via CFBD, Sagarin scraper, Massey scraper → `power_ratings_comparison` table, z-score normalized, Sunday cron, dashboard widget) | v1 |
| 8 | Groq → Claude Sonnet swap + Prompt Eval Agent (intentional Anthropic API portfolio signal) | v1 |
| 9 | CLV dashboard + subscriber tracker (soft launch, $25/month) | v1 launch |
| 10 | LangGraph multi-agent orchestration crew | v2 |
| 11 | Bayesian capstone — full in-season updating at scale | v2 |
| Launch | August 2026 | 🎯 |

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
- Calibration: Platt scaling (`CalibratedClassifierCV`) applied as of Phase 5. Raw prob preserved as `raw_win_prob`.

### Preseason Composite
- 72.87% backtest accuracy (2024)
- Weights: SP+ 25%, Recruiting 20%, Returning prod 20%, Portal 20%, Coach 15%
- 136 FBS teams rated for 2026

---

## Deferred Decisions

| Item | Phase |
|---|---|
| `spread_diff` as live feature (reintroduce using actual opening/closing lines from DB) | 7 |
| Weather integration | 7 |
| Power ratings pipeline (SP+ via CFBD, Sagarin + Massey scrapers → `power_ratings_comparison`) | 7 |
| Spread display bug fix (too many decimals) | 7 |
| Blowout filter (`abs(spread) <= 20`) | 7 |
| Tighter `model_spread_diff` threshold (`>= 5.0`) | 7 |
| Delete/undo on history page | 7 |
| Groq → Claude Sonnet swap + Prompt Eval Agent | 8 |
| CLV dashboard | 9 |
| Subscriber tracker | 9 |
| SendGrid custom domain + sender authentication (emails landing in junk) | 9 |
| LangGraph multi-agent architecture | 10 |
| Bayesian capstone | 11 |
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
ADMIN_API_KEY=
SENDGRID_API_KEY=
NOTIFY_EMAIL=
```

**Vercel dashboard**
```
VITE_API_URL=https://cfb-agent-production.up.railway.app
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_ADMIN_API_KEY=
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

*Last updated: Phase 5 complete. Platt scaling live, AI explanations wired to pick approval, 45 tests passing. pick_explanations migration run in Supabase. Next: Phase 6 — Bayesian updating.*
