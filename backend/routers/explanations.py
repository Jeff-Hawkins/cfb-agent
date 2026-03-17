"""Router for the /explanations endpoints.

Provides GET /explanations/{pick_id} to fetch a stored explanation and
POST /explanations/generate/{pick_id} (admin-protected) to trigger
AI explanation generation for a pick.
"""

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

from db.database import query_db
from routers.picks import _require_admin
from tools.explanation_generator import generate_and_store_explanation

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer()


@router.get("/{pick_id}")
def get_explanation(pick_id: str):
    """Return the stored AI explanation for a pick.

    Args:
        pick_id: UUID string of the pick.

    Returns:
        Dict with explanation_short, explanation_full, feature_snapshot,
        model_version, and generated_at fields.

    Raises:
        HTTPException 404 if no explanation exists for this pick_id.
    """
    df = query_db(
        f"SELECT * FROM pick_explanations WHERE pick_id = '{pick_id}' LIMIT 1"
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="Explanation not found for this pick.")
    row = df.iloc[0].to_dict()
    return row


@router.post("/generate/{pick_id}")
def generate_explanation(
    pick_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(_require_admin),
):
    """Trigger AI explanation generation for a pick (admin only).

    Calls generate_and_store_explanation() and returns the result.

    Args:
        pick_id: UUID string of the pick to generate an explanation for.
        background_tasks: FastAPI BackgroundTasks injected by the framework.

    Returns:
        Dict with the stored explanation fields.

    Raises:
        HTTPException 404 if the pick_id is not found in the picks table.
        HTTPException 500 on unexpected generation errors.
    """
    try:
        result = generate_and_store_explanation(pick_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Explanation generation failed for pick %s: %s", pick_id, exc)
        raise HTTPException(status_code=500, detail="Explanation generation failed.")

    return result
