# API Skill — cfb-agent

## Runtime
FastAPI on Railway. Entry point: `backend/main.py`.
Live URL: `https://cfb-agent-production.up.railway.app`
backend/ is self-contained — all dependencies (db/, models/, tools/) must be copied into backend/.

## Auth
Admin endpoints require `X-Admin-Key` header.
Key stored in Railway env as `ADMIN_API_KEY`.
Never hardcode the key. Never log it.

## Key Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /games | None | FBS games with model predictions |
| GET | /picks | None | Approved picks, public |
| GET | /picks/history | None | Full pick history with outcomes |
| GET | /rankings | None | Preseason composite rankings |
| GET | /clv/summary | None | CLV summary stats |
| GET | /clv/picks | None | Pick-level CLV table |
| POST | /admin/flag | Admin | Flag value picks |
| POST | /admin/picks/{id}/approve | Admin | Approve a flagged pick |
| POST | /admin/picks/{id}/reject | Admin | Reject a flagged pick |
| POST | /admin/lines/snapshot | Admin | Snapshot closing lines |
| POST | /admin/outcomes/refresh | Admin | Pull game outcomes |
| POST | /admin/clv/calculate | Admin | Calculate CLV records |

## Response Conventions
- All list endpoints return JSON arrays
- All admin endpoints return `{"status": "ok", "message": "..."}` on success
- Errors return `{"detail": "..."}` with appropriate HTTP status code
- game_id is the CFBD integer game ID — used as join key across all tables

## CORS
Configured in `backend/main.py`. Vercel frontend URL must be in allowed origins.
When adding new Railway deploys or preview URLs, update CORS origins list.

## Adding New Endpoints
1. Add route to appropriate router file in `backend/routers/`
2. Add any new DB queries to `backend/db/`
3. Update this file with the new endpoint
4. Add test to `tests/test_api.py`
5. Copy updated tools/ or db/ into backend/ before deploying

## Environment Variables (Railway)
DATABASE_URL, ADMIN_API_KEY, GROQ_API_KEY, SENDGRID_API_KEY
All set in Railway dashboard — never in code.
