"""
DiaIntel — Drug Routes
API endpoints for drug insights and timeline.
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugInsights, DrugTimeline

logger = logging.getLogger("diaintel.routes.drugs")
router = APIRouter()


@router.get("/drug/{drug_name}/insights", response_model=DrugInsights)
async def get_drug_insights(drug_name: str, db: Session = Depends(get_db)):
    """
    Get comprehensive insights for a specific drug.

    Returns: top AEs, sentiment score, post count, severity breakdown, drug metadata.
    Cache: 300 seconds.

    Implemented in Step 8.
    """
    start_time = time.time()

    # TODO: Implement in Step 8
    # - Query drug_stats_cache for pre-computed stats
    # - Query ae_signals for top AEs with severity breakdown
    # - Query sentiment_scores for overall sentiment
    # - Use Redis cache with 300s TTL

    raise HTTPException(
        status_code=501,
        detail=f"Drug insights endpoint not yet implemented (Step 8). Drug: {drug_name}"
    )


@router.get("/drug/{drug_name}/timeline", response_model=DrugTimeline)
async def get_drug_timeline(drug_name: str, db: Session = Depends(get_db)):
    """
    Get monthly sentiment and AE frequency for last 12 months.

    Cache: 300 seconds.

    Implemented in Step 8.
    """
    start_time = time.time()

    # TODO: Implement in Step 8
    # - Query sentiment_scores grouped by month
    # - Query ae_signals grouped by month
    # - Return 12 months of data points

    raise HTTPException(
        status_code=501,
        detail=f"Drug timeline endpoint not yet implemented (Step 8). Drug: {drug_name}"
    )
