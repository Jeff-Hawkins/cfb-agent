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
│   ├── stats_fetcher.py
│   ├── fetch_outcomes.py           # Phase 7 ✅
│   ├── snapshot_closing_lines.py   # Phase 7 ✅
│   ├── calculate_clv.py            # Phase 7 ✅
│   ├── ppa_fetcher.py              # Phase 8A ✅
│   ├── advanced_stats_updater.py   # Phase 8A ✅
│   ├── massey_scraper.py           # Phase 8A ✅
│   └── utils/
│       └── team_transformer.py     # Phase 8A ✅
├── db/
│   ├── database.py
│   ├── schema.py
│   └── migrations/
│       ├── 002_picks_table.sql
│       ├── 003_pick_explanations.sql
│       └── 003_phase7_tables.sql    # Phase 7 ✅
├── models/
│   ├── win_probability.py
│   ├── preseason_ratings.py
│   └── saved/
│       ├── win_prob_model_v2.pkl
│       ├── isotonic_calibrator_v2.joblib
│       └── feature_cols_v2.pkl
├── agent/
│   └── orchestrator.py
├── backend/                        # FastAPI — deployed on Railway
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── nixpacks.toml
│   ├── db/                         # copied from root db/ for Railway
│   ├── models/                     # copied from root models/ for Railway
│   ├── routers/
│   │   ├── admin_pipeline.py       # Phase 7 ✅
│   │   ├── clv.py                  # Phase 7 ✅
│   │   └── ...
│   ├── tools/                      # copied from root tools/ for Railway
│   └── services/
├── frontend/                       # React frontend — deployed on Vercel
│   ├── src/
│   │   ├── pages/
│   │   │   ├── CLVDashboard.jsx    # Phase 7 ✅
│   │   │   └── ...
│   │   └── ...
├── .github/
│   └── workflows/
│       ├── weekly_pipeline.yml
│       ├── cron_sunday.yml         # Phase 7 ✅
│       └── cron_tuesday.yml        # Phase 7 ✅
├── tests/
│   ├── test_phase7.py              # Phase 7 ✅
│   ├── test_phase8a.py             # Phase 8A ✅
│   └── ...
└── ...
```

---

## Completed Phases

### Phase 1–6 (archived) ✅
- SQLite → Supabase (PostgreSQL) migration
- LightGBM v1 (21 features)
- FastAPI backend & React frontend
- Supabase Auth & Pick Flagging logic
- AI Explanations via Groq
- Railway/Vercel deployment
- Bayesian Recalibration pipeline

### Phase 6.5 ✅
- **V2 model productionized** — 17 features, isotonic calibration
  - **Accuracy:** 64.59% | **Brier:** 0.2152 (2025 holdout)
  - **New Features:** `offense_lineYards_diff`, `defense_stuffRate_diff` (top 5 importance)
  - **Artifacts:** `win_prob_model_v2.pkl`, `isotonic_calibrator_v2.joblib`, `feature_cols_v2.pkl`

### Phase 7 ✅
- **Artifact Cleanup** — V1 models deleted; `platt_scaler_v2` renamed to `isotonic_calibrator_v2`.
- **Database Expansion** — Added `game_outcomes`, `closing_lines`, `clv_records`, `cron_log` tables.
- **Outcome Pipeline** — `tools/fetch_outcomes.py` for score fetching and ATS resolution.
- **CLV Engine** — `tools/snapshot_closing_lines.py` and `tools/calculate_clv.py`.
- **Admin API** — `/admin/outcomes/refresh`, `/admin/clv/calculate`, `/admin/lines/snapshot`.
- **CLV Dashboard** — Public frontend page at `/clv` with summary stats and pick-level tracking.
- **Conference Tagging** — G5/P4 labels and filters on Games page.
- **Pick Spread Capture** — `pick_spread` now recorded at the moment of approval.
- **Cron Stubs** — GitHub Actions workflows for Sunday/Tuesday automation.
- **113 tests passing**

### Phase 8A ✅
- **Data Expansion** — Extended `advanced_stats` with `success_rate` and `defense_havoc_total`.
- **PPA Pipeline** — `tools/ppa_fetcher.py` for per-team PPA and success rates.
- **Massey Scraper** — `tools/massey_scraper.py` for scraping Kenneth Massey's ratings.
- **Power Ratings Comparison** — Added `power_ratings_comparison` table with Z-score logic.
- **Centralized Utils** — `tools/utils/team_transformer.py` for canonical CFBD name mapping.
- **Cron Update** — Sunday pipeline now includes PPA and Massey rating refreshes.
- **116 tests passing**

---

## Upcoming Phases

| Phase | Description | Status |
|---|---|---|
| 8B | Power Ratings Visualization & Sagarin Integration | 🔜 Next |
| 9 | CLV dashboard enhancements + Betstamp/Pikkit third-party verification | 🔜 |
| Launch | August 2026 — portfolio piece complete | 🎯 |

---

## Conventions & Non-Negotiables

- **Tests required** before any function ships
- **Docstrings on every module**
- **Never hardcode credentials** — `.env` locally, Railway/Vercel dashboards in prod
- **No Co-Authored-By in commits**
- **backend/ is self-contained** — any root module used by API must be copied into `backend/`
- **Use query_db()** for all database reads; `engine.begin()` for writes/updates.

---

## Database Tables (New in Phase 7/8A)

- **`game_outcomes`**: Final scores and ATS resolution.
- **`closing_lines`**: Final market lines before kickoff.
- **`clv_records`**: Per-pick CLV (pick_spread - closing_spread).
- **`cron_log`**: Audit trail for automated pipelines.
- **`ppa_ratings`**: Per-team PPA and success rates.
- **`power_ratings_comparison`**: Massey vs SP+ comparison with Z-scores.
- **`picks.pick_spread`**: Column added to capture spread at approval time.

---

## Cron Infrastructure

- **Sunday (8pm ET)**: `outcomes/refresh`, `ratings/refresh` (Manual via GitHub Action until Aug 2026).
- **Tuesday (12pm ET)**: `stats/refresh` (Advanced stats and power ratings).

---

*Last updated: Phase 8A complete. Portfolio-focused roadmap: 1 phase remaining (8B: power ratings visualization). Target: August 2026.*

## Skills

Modular reference files in `skills/`. Read the relevant skill before starting any task in that domain.

| Skill | File | Read Before |
|---|---|---|
| Database | `skills/db.md` | Any DB query, migration, or schema change |
| Predictions | `skills/predictions.md` | Any change to flag logic, thresholds, or model inference |
| API | `skills/api.md` | Adding endpoints, modifying routers, Railway deploys |
| Frontend | `skills/frontend.md` | Any React component, page, or Vercel deploy |
| Testing | `skills/testing.md` | Writing any test or running the suite |
| Model | `skills/model.md` | ⚠️ Not built yet — pending V3 confirmation |

