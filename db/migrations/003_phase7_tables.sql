-- Phase 7 Database Migrations
-- Artifact cleanup, outcome pipeline, CLV tracking, and metadata tagging.

-- Table 1: game_outcomes
-- Stores final scores and ATS resolution for completed games.
-- ATS resolution logic:
--   spread is from home team perspective (negative = home favored)
--   margin = home_score - away_score
--   home covers if: margin > -spread (home wins by more than they were favored, 
--     OR home loses by less than they were the underdog)
--   away covers if: margin < -spread
--   push if: margin == -spread
CREATE TABLE IF NOT EXISTS game_outcomes (
    game_id         TEXT PRIMARY KEY,
    home_team       TEXT,
    away_team       TEXT,
    home_score      INTEGER,
    away_score      INTEGER,
    game_result     TEXT,      -- 'home_win' | 'away_win' | 'push'
    ats_result      TEXT,      -- 'home_covered' | 'away_covered' | 'push'
    home_covered    BOOLEAN,
    away_covered    BOOLEAN,
    fetched_at      TIMESTAMPTZ DEFAULT now()
);

-- Table 2: closing_lines
-- Stores the final market line before kickoff.
CREATE TABLE IF NOT EXISTS closing_lines (
    game_id         TEXT PRIMARY KEY,
    season          INTEGER,
    week            INTEGER,
    home_team       TEXT,
    away_team       TEXT,
    closing_spread  DECIMAL,   -- same sign convention as betting_lines
    closing_total   DECIMAL,
    source          TEXT,      -- 'consensus' | 'draftkings' | 'manual'
    snapped_at      TIMESTAMPTZ DEFAULT now()
);

-- Table 3: clv_records
-- Stores CLV calculation per approved pick after game completes.
CREATE TABLE IF NOT EXISTS clv_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pick_id         UUID NOT NULL,   -- FK to picks.id
    game_id         TEXT NOT NULL,
    pick_team       TEXT,
    pick_spread     DECIMAL,   -- spread stored at approval time (pick team perspective)
    closing_spread  DECIMAL,   -- from closing_lines table (pick team perspective)
    clv             DECIMAL,   -- pick_spread - closing_spread (positive = beat the close)
    clv_positive    BOOLEAN,
    outcome         TEXT,      -- WIN | LOSS | PUSH (from game_outcomes)
    recorded_at     TIMESTAMPTZ DEFAULT now()
);

-- Table 4: cron_log
-- Audit trail for all cron/pipeline runs.
CREATE TABLE IF NOT EXISTS cron_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name        TEXT NOT NULL,
    run_at          TIMESTAMPTZ DEFAULT now(),
    records_updated INTEGER DEFAULT 0,
    errors          TEXT,
    status          TEXT   -- 'success' | 'partial' | 'failed'
);

-- Migration: add pick_spread column to picks table if it doesn't exist
-- This column stores the spread at approval time (from pick team's perspective).
-- Sign convention: negative = pick team is favored.
--   If pick_team == home_team: pick_spread = betting_lines.spread
--   If pick_team == away_team: pick_spread = -1 * betting_lines.spread
ALTER TABLE picks ADD COLUMN IF NOT EXISTS pick_spread DECIMAL;
