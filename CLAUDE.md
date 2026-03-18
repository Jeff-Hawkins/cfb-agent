# CLAUDE.md — CFB Agent Project Briefing

> This file is read by Claude Code at the start of every session.
> Update at the end of each phase before committing.

---

## Project Overview

**Name:** CFB Agent
**Purpose:** End-to-end AI sports analytics portfolio piece. Demonstrates predictive modeling, LLM orchestration, real-time data pipelines, and full-stack production deployment. No subscriptions or monetization in current plan — CLV dashboard and public track record are the primary credibility metrics.
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
- Post-phase fix: `ret_totalppa` / `ret_percentppa` must be accessed as lowercase — `query_db` lowercases all unquoted AS aliases
- Post-phase fix: `groq==1.1.0` added to `backend/requirements.txt` — was missing, caused ModuleNotFoundError on Railway

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

### Frontend Bug Fixes (commit `003d636`) ✅
- **AI Analysis on PickHistoryPage** — fetches `GET /explanations/{pick_id}` in parallel after picks load (non-blocking); renders `explanation_short` as a second table row below each pick under an "AI Analysis" label in muted xs text; 404 and network errors fail silently
- **Spread decimal display** — `PendingPicksPage` and `PickHistoryPage` now wrap all `spread` and `model_spread_diff` values with `toFixed(1)` — `-21.8` instead of `-21.8333...`

### Railway Deploy ✅
- Live URL: `https://cfb-agent-production.up.railway.app`
- Dockerfile used (nixpacks could not resolve libgomp)
- `libgomp1` installed via apt in Dockerfile for LightGBM
- `sqlalchemy` and `psycopg2-binary` in `backend/requirements.txt`
- `DATABASE_URL` uses Supabase Transaction Pooler (port 6543, IPv4 compatible)
- `backend/db/` and `backend/models/` copied into backend for Railway self-containment
- All endpoints tested live

### Phase 6 (commits since Phase 5) ✅
- **Corrected flag logic** — real spread_diff using `betting_lines.spread`, home/away sign-aware formula
- **Updated thresholds** — `abs(spread)<=17`, `win_prob>=0.65`, `abs(spread_diff)>=5.0`
- **`POST /picks/recalculate-spreads`** — backfills corrected spread_diff on existing picks
- **`GET /picks/public`** — public endpoint, sorted by abs(model_spread_diff) descending
- **`GET /games/weekly`** — FBS-only, batch prediction, model vs Vegas comparison, blowout filter
- **Bayesian updater** — `tools/bayesian_updater.py`, weekly Platt scaler recalibration, SendGrid notification
- **`POST /bayesian/update`** + **`GET /bayesian/performance`** — admin + public endpoints
- **Public picks page** — `/picks` route, no auth, AI Analysis, Pick Spread/Model Line/Edge display
- **Games page** — replaces Schedule, `/games` route, FBS only, confidence badges, 🔥 value pick flag
- **AI explanation at flag time** — background task fires on insert, not on approval
- **Shared constants** — `backend/constants.py` — single source of truth for all thresholds
- **Batch prediction** — `predict_win_probability_batch()` — 10x performance improvement
- **Groq prompt fix** — historical framing for all feature statistics
- **88 tests passing**

---

## Current Phase

### Next: Phase 7 — Line Value Engine + Weather + Power Ratings Pipeline 🔄

Phase 6 complete. All deliverables live in production:
- ✅ Corrected spread_diff formula (real betting lines, home/away sign convention)
- ✅ Updated flag thresholds (abs(spread)<=17, win_prob>=0.65, abs(spread_diff)>=5.0)
- ✅ Public picks page (/picks — no auth, fully open Season 1)
- ✅ Games page replacing Schedule (/games — FBS only, win_prob>=0.55, model vs Vegas)
- ✅ Bayesian updating pipeline (weekly performance tracking, Platt scaler recalibration)
- ✅ AI explanation generated at flag time (not approval time)
- ✅ Shared constants file (backend/constants.py)
- ✅ Batch prediction (47 games in ~5s vs 2+ minutes previously)
- ✅ 88 tests passing

---

## Phase 6 Scope (archived)

### Flag Logic Corrections (pulling forward from Phase 7)
- **Corrected spread_diff formula** — uses actual `betting_lines.spread` (not approximation)
  - If pick_team = home_team: `model_implied_spread = -1 * (win_prob - 0.5) * 28`
  - If pick_team = away_team: `model_implied_spread = (win_prob - 0.5) * 28`
  - `spread_diff = actual_spread - model_implied_spread`
- **Updated flag thresholds:**
  - `abs(spread) <= 17` — removes blowouts
  - `win_prob >= 0.65` — model confidence floor (unchanged)
  - `abs(spread_diff) >= 5.0` — real model vs market disagreement
- **Sign convention confirmed:** negative spread = home team favored

### Public Picks Page (`/picks`)
- No auth required — fully open Season 1
- Shows all approved picks for current season/week
- Each pick displays: matchup, pick team, win prob, confidence badge, spread (toFixed(1)), AI Analysis (`explanation_short`)
- Header: overall ATS record + ROI
- Week filter
- No CLV data yet (Phase 9)

### Bayesian Updating
- In-season model recalibration as 2025 results come in

---

## Upcoming Phases

| Phase | Description | Status |
|---|---|---|
| 7 | Line value engine + weather integration + power ratings pipeline (SP+ via CFBD, Sagarin scraper, Massey scraper → `power_ratings_comparison` table, z-score normalized, Sunday cron, full model comparison on Games page) | 🔜 Next |
| 8 | CLV dashboard + public track record (Betstamp/Pikkit third-party verification) | 🔜 |
| Launch | August 2026 — portfolio piece complete | 🎯 |
| 10 | LangGraph multi-agent + NFL agent v1 (post-launch) | Future |
| 12 | CBB agent + March Madness (2027) | Future |

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
| Blowout filter and spread_diff threshold | ✅ Pulled into Phase 6 |
| Games page (model vs Vegas comparison) | ✅ Built in Phase 6 — SP+/Sagarin/Massey columns deferred to Phase 7 |
| Spread display bug fix (too many decimals) | ✅ Fixed in Phase 5 post-patch |
| Delete/undo on history page | 7 |
| Groq → Claude Sonnet swap | Deferred indefinitely — LLM stays on Groq (free tier) |
| CLV dashboard | 8 |
| Betstamp/Pikkit track record verification | 8 |
| LangGraph multi-agent + NFL agent | Phase 10 (post-launch) |
| CBB agent | Phase 12 (2027) |
| Subscriptions + monetization | Not in current plan — portfolio piece only |
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

*Last updated: Phase 6 complete. Portfolio-focused roadmap: 2 phases remaining (7: power ratings pipeline, 8: CLV dashboard). No monetization, no subscriptions, LLM stays on Groq. Target: August 2026.*
