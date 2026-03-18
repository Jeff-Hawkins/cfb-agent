# GEMINI.md — Project Mandates & Core Logic

> This file contains foundational mandates for the CFB Agent project.
> It takes precedence over general workflows and tool defaults.

---

## Project Overview

**Name:** CFB Agent
**Purpose:** End-to-end AI sports analytics system. Demonstrates predictive modeling, LLM orchestration, real-time data pipelines, and full-stack production deployment.
**Target users:** CFB bettors who want model-backed win probability, line value flags, and verified pick tracking (CLV as primary credibility metric).

---

## Current Status (Phase 6.5 ✅)

- **V2 model productionized** — 17 features, isotonic calibration
  - **Accuracy:** 64.59% | **Brier:** 0.2152 (2025 holdout)
  - **New Features:** `offense_lineYards_diff`, `defense_stuffRate_diff` (top 5 importance)
  - **Neutral Defaults:** 0.009 for line yards diff, 0.0016 for stuff rate diff
  - **Absolute Fallbacks:** 3.04 (yards) and 0.179 (stuff rate) for single-team data gaps
  - **Data source:** `advanced_stats` table, populated by `fetch_advanced_stats()`
  - **Artifacts:** `win_prob_model_v2.pkl`, `platt_scaler_v2.joblib` (isotonic), `feature_cols_v2.pkl`
  - **Note:** `platt_scaler_v2.joblib` is actually isotonic — rename in Phase 7 cleanup
  - **V1 cleanup:** artifacts flagged for deletion in Phase 7
- **107 tests passing** — `tests/test_model_retrain.py` updated for 17 features

---

## Core Logic & Betting Mandates

### 1. Win Probability Model (LightGBM v2)
- **Architecture:** LightGBM classifier + Isotonic calibration (`CalibratedClassifierCV`).
- **Features (17 key signals):** 
  - SP+ Matchup differentials (4 features)
  - 3yr Recruiting Average & Team Talent Composite
  - Returning Production (PPA & Percentage)
  - Transfer Portal Net Rating
  - Coaching (New coach flag & Career win percentage)
  - Elo Rating Differential
  - Line Play (Line Yards & Stuff Rate differentials)
  - Home Field Advantage & Neutral Site flags
- **Inference Strategy:** All features use **Season-1** lookups to ensure preseason data is available at prediction time.

### 2. Betting & Flagging Logic
- **Flag Thresholds:**
  - `Win Probability >= 65%`: Model confidence floor.
  - `Abs(Consensus Spread) <= 17`: Blowout filter.
  - `Abs(Spread Difference) >= 5.0`: Model vs Market disagreement.
- **Directional Spread Formula:**
  - Home Pick: `model_implied = -1 * (win_prob - 0.5) * 28`
  - Away Pick: `model_implied = (win_prob - 0.5) * 28`
  - `spread_diff = actual_spread - model_implied`

---

## Project Rules & Python Coding Style

### 1. General Standards
- **Docstrings Required:** Every module and function must have a clear docstring.
- **Type Hinting:** Use Python type hints for all function signatures.
- **No Hardcoded Credentials:** Use `.env` locally and environment variables in production.

### 2. Backend & API
- **Surgical Changes:** Apply targeted updates. Do not refactor unrelated code.
- **Redundancy Mandate:** Any root module used by the FastAPI backend must be copied into the `backend/` directory.
- **Auth Enforcement:** Administrative POST/PUT/DELETE endpoints must use `_require_admin`.

### 3. Data & Modeling
- **Inference Integrity:** All model features at inference time must be "pre-game" (Season-1).
- **Test-Driven Development:** Update tests in `tests/` before shipping logic changes.
- **Database Access:** Use `query_db` for reads and `save_to_db` for writes.

---

## Current Phase

### Next: Phase 7 — Line Value Engine + Weather + Power Ratings Pipeline 🔄
