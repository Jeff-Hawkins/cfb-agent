# Database Skill — cfb-agent

## Connection
Always use `query_db()` from `db/database.py` for ALL database access.
Never use raw psycopg2 or SQLAlchemy sessions directly.
DATABASE_URL = Supabase Transaction Pooler, port 6543, IPv4.

## Table Reference

### picks
id, game_id, home_team, away_team, pick_team, win_probability,
model_spread, actual_spread, spread_diff, model_edge, flagged,
approved, rejected, outcome, pick_spread, season,
created_at, updated_at

### betting_lines
game_id, home_team, away_team, spread, over_under, home_moneyline,
away_moneyline, game_date, season, week, source, created_at
Sign convention: negative spread = home team favored.
One consensus row per game, averaged across DraftKings/Bovada/ESPN Bet.

### game_outcomes
id, game_id, home_team, away_team, home_score, away_score,
winner, ats_winner, total_result, season, week, recorded_at

### closing_lines
id, game_id, home_team, away_team, closing_spread,
closing_total, source, recorded_at, season

### clv_records
id, pick_id, game_id, open_spread, closing_spread, pick_spread,
clv, clv_positive, season, calculated_at

### cron_log
id, job_name, status, message, rows_affected, ran_at

### pick_explanations
id, pick_id, short_narrative, full_narrative, feature_snapshot,
model_version, created_at

### power_ratings (Phase 8 — if exists)
team, sp_plus, sagarin, massey, composite_z, season, updated_at

## Common Patterns

### Basic query
```python
results = query_db("SELECT * FROM picks WHERE approved = TRUE ORDER BY created_at DESC")
```

### Parameterized query
```python
results = query_db(
    "SELECT * FROM picks WHERE season = %s AND approved = TRUE",
    (season,)
)
```

### Join example
```python
results = query_db("""
    SELECT p.id, p.pick_team, cr.clv, cr.clv_positive
    FROM picks p
    JOIN clv_records cr ON cr.pick_id = p.id
    WHERE p.season = %s
""", (season,))
```

## Known Gotchas
- PostgreSQL lowercases all unquoted AS aliases — use lowercase column names in queries
- Always use explicit table aliases on joins to avoid ambiguous column errors (e.g. `cr.clv` not `clv`)
- Verify column names against this file before writing any query — do not guess
- `spread_diff` formula: home pick → `model_implied = -1 * (win_prob - 0.5) * 28`; away pick → `(win_prob - 0.5) * 28`
- backend/ is self-contained — db/ must be copied into backend/db/ for Railway deploys
