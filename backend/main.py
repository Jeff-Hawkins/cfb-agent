"""FastAPI application entry point for the CFB agent backend.

Mounts the /matchup, /rankings, and /games routers and exposes a /health endpoint.
Adds the repo root to sys.path so routers can import from models/ and db/.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import matchup, rankings, games, picks, explanations, bayesian, admin_pipeline, clv

app = FastAPI(title="CFB Agent API")

# Allow all origins for solo portfolio piece
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matchup.router,      prefix="/matchup",      tags=["matchup"])
app.include_router(rankings.router,     prefix="/rankings",     tags=["rankings"])
app.include_router(games.router,        prefix="/games",        tags=["games"])
app.include_router(picks.router,        prefix="/picks",        tags=["picks"])
app.include_router(explanations.router, prefix="/explanations", tags=["explanations"])
app.include_router(bayesian.router,    prefix="/bayesian",    tags=["bayesian"])
app.include_router(admin_pipeline.router, prefix="/admin",      tags=["admin"])
app.include_router(clv.router,          prefix="/clv",          tags=["clv"])

@app.get("/health")
def health():
    """Return a simple liveness check."""
    return {"status": "ok"}
