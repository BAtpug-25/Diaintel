"""
DiaIntel — Misinformation Routes
API endpoint for the misinformation monitor feed.
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import MisinfoFeed

logger = logging.getLogger("diaintel.routes.misinfo")
router = APIRouter()


@router.get("/misinfo/feed", response_model=MisinfoFeed)
async def get_misinfo_feed(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence filter"),
    reviewed: bool = Query(None, description="Filter by reviewed status"),
    db: Session = Depends(get_db),
):
    """
    Get paginated feed of flagged misinformation posts.

    Returns: post excerpt, claim text, confidence, flag reason,
    reviewed status.

    Cache: 60 seconds.

    Implemented in Step 8.
    """
    start_time = time.time()

    # TODO: Implement in Step 8
    # - Query misinfo_flags with pagination
    # - Filter by confidence >= min_confidence
    # - Optional filter by reviewed status
    # - Join with processed_posts for excerpt
    # - Use Redis cache with 60s TTL

    raise HTTPException(
        status_code=501,
        detail="Misinfo feed endpoint not yet implemented (Step 8)"
    )


@router.patch("/misinfo/{flag_id}/review")
async def mark_as_reviewed(flag_id: int, db: Session = Depends(get_db)):
    """
    Mark a misinformation flag as reviewed.

    No delete option — only flag or label.

    Implemented in Step 8.
    """
    start_time = time.time()

    # TODO: Implement in Step 8
    # - Update misinfo_flags.reviewed = True
    # - Never delete, only update

    raise HTTPException(
        status_code=501,
        detail=f"Mark reviewed endpoint not yet implemented (Step 8). Flag ID: {flag_id}"
    )
