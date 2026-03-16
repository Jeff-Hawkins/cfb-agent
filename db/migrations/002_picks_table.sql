-- Migration 002: Create picks table
-- Run against Supabase (PostgreSQL) before deploying Phase 4.5.

CREATE TABLE IF NOT EXISTS picks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id             TEXT NOT NULL,
  season              INTEGER,
  week                INTEGER,
  home_team           TEXT,
  away_team           TEXT,
  pick_team           TEXT,
  win_probability     FLOAT,
  spread              FLOAT,
  model_spread_diff   FLOAT,
  confidence_label    TEXT,
  approved            BOOLEAN DEFAULT FALSE,
  rejected            BOOLEAN DEFAULT FALSE,
  approval_timestamp  TIMESTAMPTZ,
  outcome             TEXT,
  ats_result          TEXT,
  clv                 FLOAT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(game_id)
);
